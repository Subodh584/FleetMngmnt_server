from rest_framework import serializers

from core.serializers import UserSerializer
from .models import (
    Vehicle, InspectionChecklist, InspectionChecklistItem,
    Inspection, InspectionResult, VehicleIssue,
)


class VehicleSerializer(serializers.ModelSerializer):
    """
    Standard serialization profile for Vehicle metadata.
    Locks timestamps to read-only since they're system-managed.
    """
    class Meta:
        model = Vehicle
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


# ---------------------------------------------------------------------------
# Inspection Checklists
# ---------------------------------------------------------------------------

class InspectionChecklistItemSerializer(serializers.ModelSerializer):
    """
    Serializes a single inspection question/step.
    """
    class Meta:
        model = InspectionChecklistItem
        fields = '__all__'


class InspectionChecklistSerializer(serializers.ModelSerializer):
    """
    Serializes an overarching checklist and automatically nests its
    constituent line items to supply clients with the full schema tree entirely.
    """
    items = InspectionChecklistItemSerializer(many=True, read_only=True)

    class Meta:
        model = InspectionChecklist
        fields = '__all__'
        read_only_fields = ['created_at']


# ---------------------------------------------------------------------------
# Inspections
# ---------------------------------------------------------------------------

class InspectionResultSerializer(serializers.ModelSerializer):
    """Output structural representation of a single checklist answer/result."""
    class Meta:
        model = InspectionResult
        fields = '__all__'
        read_only_fields = ['inspection']


class InspectionSerializer(serializers.ModelSerializer):
    """Output representation of a submitted Inspection mapping down to its embedded results."""
    results = InspectionResultSerializer(many=True, read_only=True)

    class Meta:
        model = Inspection
        fields = '__all__'
        read_only_fields = ['submitted_at', 'created_at', 'reviewed_by', 'reviewed_at']


class InspectionResultWriteSerializer(serializers.Serializer):
    """
    Deserialization shell specifically utilized to parse embedded JSON objects representing 
    inspection results dynamically inside a unified Inspection POST payload.
    """
    checklist_item_id = serializers.IntegerField()
    result = serializers.ChoiceField(choices=InspectionResult.RESULT_CHOICES)
    notes = serializers.CharField(required=False, default='', allow_blank=True)
    photo_url = serializers.URLField(required=False, default='', allow_blank=True)


class InspectionCreateSerializer(serializers.ModelSerializer):
    """
    Create inspection with nested results simultaneously managed in a single network request.
    Leverages transaction-safe bulk saving logic.
    """

    results = InspectionResultWriteSerializer(many=True, write_only=True)

    class Meta:
        model = Inspection
        fields = [
            'trip', 'vehicle', 'checklist', 'inspection_type', 'notes',
            'assigned_to_manager', 'results',
        ]

    def create(self, validated_data):
        """
        Coordinates the creation of the parent Inspection against multiple
        simultaneous InspectionResult checks while estimating an initial risk/flag status.
        """
        results_data = validated_data.pop('results')
        driver = self.context['request'].user
        
        # Auto-detect inspection hazards: one fail flags the entire submission.
        has_fail = any(r['result'] == 'fail' for r in results_data)
        overall_status = 'flagged' if has_fail else 'approved'

        # Derive assigned_to_manager implicitly from the parent trip routing if not explicitly requested
        if 'assigned_to_manager' not in validated_data or validated_data['assigned_to_manager'] is None:
            trip = validated_data.get('trip')
            if trip and trip.assigned_by_id:
                validated_data['assigned_to_manager'] = trip.assigned_by

        inspection = Inspection.objects.create(driver=driver, overall_status=overall_status, **validated_data)
        
        # Batch insert results array mapping foreign keys to the newly constructed inspection
        result_objects = [
            InspectionResult(
                inspection=inspection,
                checklist_item_id=r['checklist_item_id'],
                result=r['result'],
                notes=r.get('notes', ''),
                photo_url=r.get('photo_url', ''),
            )
            for r in results_data
        ]
        InspectionResult.objects.bulk_create(result_objects)
        return inspection

    def to_representation(self, instance):
        """Re-map the created objects through the standard reading serializer."""
        return InspectionSerializer(instance).data


# ---------------------------------------------------------------------------
# Vehicle Issues
# ---------------------------------------------------------------------------

class VehicleIssueSerializer(serializers.ModelSerializer):
    """Standard read/write structure for reporting specific Vehicle flaws or breakdowns."""
    class Meta:
        model = VehicleIssue
        fields = '__all__'
        read_only_fields = ['reported_by', 'reported_at', 'updated_at']


# ---------------------------------------------------------------------------
# Detailed Serializers for Fleet-Manager Issue View
# ---------------------------------------------------------------------------

class InspectionResultDetailSerializer(serializers.ModelSerializer):
    """Enriches standard result payloads by appending the real readable question/item text."""
    checklist_item_name = serializers.CharField(source='checklist_item.item_name', read_only=True)

    class Meta:
        model = InspectionResult
        fields = ['id', 'checklist_item', 'checklist_item_name', 'result', 'notes', 'photo_url']


class InspectionDetailSerializer(serializers.ModelSerializer):
    """Enriches an inspection loadout with explicit detailed results."""
    results = InspectionResultDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Inspection
        fields = '__all__'


class VehicleIssueDetailSerializer(serializers.ModelSerializer):
    """
    Detail serializer used uniquely for deep retrieve actions.

    Foreign-key fields maintain their raw integer IDs natively (`vehicle`, `reported_by`, `inspection`,
    `assigned_to_manager`) enabling the iOS mapping schema to decode them transparently as optional JSON ints.
    
    Nested expansion objects are stored defensively beneath `*_detail` dictionary keys so the 
    subsequent client-side mapping models parse them independently without crashing atop native IDs.
    """
    vehicle_detail = VehicleSerializer(source='vehicle', read_only=True)
    reported_by_detail = UserSerializer(source='reported_by', read_only=True)
    inspection_detail = InspectionDetailSerializer(source='inspection', read_only=True)
    assigned_to_manager_detail = UserSerializer(source='assigned_to_manager', read_only=True)

    class Meta:
        model = VehicleIssue
        fields = '__all__'
