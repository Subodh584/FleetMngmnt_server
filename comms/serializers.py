from rest_framework import serializers

from .models import Message, Notification, SOSAlert


class MessageSerializer(serializers.ModelSerializer):
    """Provides internal chat histories dynamically, keeping exact ingest stamps natively un-editable."""
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['sender', 'is_read', 'read_at', 'sent_at']


class NotificationSerializer(serializers.ModelSerializer):
    """Maps global async push-payloads safely strictly masking identity override fields inherently."""
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


class SOSAlertSerializer(serializers.ModelSerializer):
    """Ensures distress timestamps globally restrict spoofed resolution tracking mechanically."""
    class Meta:
        model = SOSAlert
        fields = '__all__'
        read_only_fields = ['driver', 'resolved', 'resolved_by', 'resolved_at', 'triggered_at']
