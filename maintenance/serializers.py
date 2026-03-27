from rest_framework import serializers

from .models import MaintenanceSchedule, MaintenanceRecord, SparePart, SparePartUsed


class SparePartSerializer(serializers.ModelSerializer):
    class Meta:
        model = SparePart
        fields = '__all__'
        read_only_fields = ['total_cost', 'created_at', 'updated_at']
        extra_kwargs = {
            'maintenance': {'required': False, 'allow_null': True},
        }


class SparePartUsedSerializer(serializers.ModelSerializer):
    class Meta:
        model = SparePartUsed
        fields = '__all__'
        read_only_fields = ['total_cost', 'created_at']


class MaintenanceScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceSchedule
        fields = '__all__'
        read_only_fields = ['scheduled_by', 'created_at', 'updated_at']


class MaintenanceRecordSerializer(serializers.ModelSerializer):
    """
    Standard read-out exposing physical maintenance tasks alongside their explicit consumption histories.
    """
    spare_parts = SparePartUsedSerializer(many=True, read_only=True)

    class Meta:
        model = MaintenanceRecord
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class SparePartInlineSerializer(serializers.ModelSerializer):
    """
    Write-only nested serializer specifically used for fast API array ingestions 
    when mapping bulk parts instantly into a new MaintenanceRecord instantiation block.
    """
    class Meta:
        model = SparePartUsed
        fields = ['part_name', 'part_number', 'quantity', 'unit_cost']


class MaintenanceRecordCreateSerializer(serializers.ModelSerializer):
    """
    Complex ingest resolver allowing frontend clients to dump 
    Maintenance bounds and nested Inventory constraints synchronously over the network.
    """
    spare_parts = SparePartInlineSerializer(many=True, required=False)

    class Meta:
        model = MaintenanceRecord
        fields = [
            'vehicle', 'schedule', 'issue', 'maintenance_type', 'description',
            'assigned_to', 'mileage_at_service', 'technician_notes', 'spare_parts',
        ]

    def create(self, validated_data):
        spare_parts_data = validated_data.pop('spare_parts', [])
        user = self.context['request'].user
        record = MaintenanceRecord.objects.create(assigned_by=user, **validated_data)
        
        # Inject explicit decoupled relationships securely.
        for sp_data in spare_parts_data:
            SparePartUsed.objects.create(maintenance=record, **sp_data)
            
        # Secure cascading lock onto the global asset map instantly.
        vehicle = record.vehicle
        vehicle.status = 'under_maintenance'
        vehicle.save(update_fields=['status', 'updated_at'])
        
        return record

    def to_representation(self, instance):
        # Prevent the user receiving a weird inbound write-object context wrapper implicitly. 
        return MaintenanceRecordSerializer(instance).data
