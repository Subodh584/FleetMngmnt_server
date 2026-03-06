from rest_framework import serializers

from .models import VehicleIssue


class VehicleIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleIssue
        fields = '__all__'
        read_only_fields = ['reported_by', 'reported_at', 'updated_at']
