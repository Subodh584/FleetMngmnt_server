from rest_framework import serializers

from .models import (
    Vehicle, InspectionChecklist, InspectionChecklistItem,
    Inspection, InspectionResult, VehicleIssue,
)


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


# ---------------------------------------------------------------------------
# Inspection checklists
# ---------------------------------------------------------------------------

class InspectionChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionChecklistItem
        fields = '__all__'


class InspectionChecklistSerializer(serializers.ModelSerializer):
    items = InspectionChecklistItemSerializer(many=True, read_only=True)

    class Meta:
        model = InspectionChecklist
        fields = '__all__'
        read_only_fields = ['created_at']


# ---------------------------------------------------------------------------
# Inspections
# ---------------------------------------------------------------------------

class InspectionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionResult
        fields = '__all__'
        read_only_fields = ['inspection']


class InspectionSerializer(serializers.ModelSerializer):
    results = InspectionResultSerializer(many=True, read_only=True)

    class Meta:
        model = Inspection
        fields = '__all__'
        read_only_fields = ['submitted_at', 'created_at', 'reviewed_by', 'reviewed_at']


class InspectionResultWriteSerializer(serializers.Serializer):
    checklist_item_id = serializers.IntegerField()
    result = serializers.ChoiceField(choices=InspectionResult.RESULT_CHOICES)
    notes = serializers.CharField(required=False, default='')
    photo_url = serializers.URLField(required=False, default='')


class InspectionCreateSerializer(serializers.ModelSerializer):
    """Create inspection with nested results in a single request."""

    results = InspectionResultWriteSerializer(many=True, write_only=True)

    class Meta:
        model = Inspection
        fields = [
            'trip', 'vehicle', 'checklist', 'inspection_type', 'notes', 'results',
        ]

    def create(self, validated_data):
        results_data = validated_data.pop('results')
        driver = self.context['request'].user
        inspection = Inspection.objects.create(driver=driver, **validated_data)
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
        return InspectionSerializer(instance).data


# ---------------------------------------------------------------------------
# Vehicle issues
# ---------------------------------------------------------------------------

class VehicleIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleIssue
        fields = '__all__'
        read_only_fields = ['reported_by', 'reported_at', 'updated_at']
