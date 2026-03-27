from rest_framework import serializers
from .models import AIChatSession, AIChatMessage


class AIChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIChatMessage
        # generated_sql is deliberately excluded — it is an internal audit field
        fields = ['id', 'role', 'content', 'created_at']


class AIChatSessionSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = AIChatSession
        fields = ['id', 'title', 'created_at', 'updated_at', 'last_message', 'message_count']

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if msg:
            return {
                'role': msg.role,
                'content': msg.content[:120] + '...' if len(msg.content) > 120 else msg.content,
            }
        return None

    def get_message_count(self, obj):
        return obj.messages.count()


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1000, trim_whitespace=True)
    session_id = serializers.IntegerField(required=False, allow_null=True)
