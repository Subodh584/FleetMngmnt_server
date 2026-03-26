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
    spare_parts = SparePartUsedSerializer(many=True, read_only=True)

    class Meta:
        model = MaintenanceRecord
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class MaintenanceRecordCreateSerializer(serializers.ModelSerializer):
    spare_parts = SparePartUsedSerializer(many=True, required=False)

    class Meta:
        model = MaintenanceRecord
        fields = [
            'vehicle', 'schedule', 'issue', 'maintenance_type', 'description',
            'assigned_to', 'mileage_at_service', 'technician_notes', 'parts_used', 'spare_parts',
        ]

    def create(self, validated_data):
        print("\n[DEBUG] RECEIVED PAYLOAD:", self.context['request'].data)
        print("[DEBUG] VALIDATED DATA:", validated_data)
        spare_parts_data = validated_data.pop('spare_parts', [])
        user = self.context['request'].user
        record = MaintenanceRecord.objects.create(assigned_by=user, **validated_data)
        print("[DEBUG] SAVED RECORD ID:", record.id)
        print("[DEBUG] SAVED PARTS_USED:", record.parts_used)
        for sp_data in spare_parts_data:
            SparePartUsed.objects.create(maintenance=record, **sp_data)
        # Set vehicle under_maintenance
        vehicle = record.vehicle
        vehicle.status = 'under_maintenance'
        vehicle.save(update_fields=['status', 'updated_at'])
        return record

    def to_representation(self, instance):
        return MaintenanceRecordSerializer(instance).data
