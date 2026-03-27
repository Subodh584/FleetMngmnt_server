from django.conf import settings
from django.db import models


class AIChatSession(models.Model):
    """Represents one conversation thread between a user and the AI assistant."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_sessions',
    )
    title = models.CharField(max_length=255, default='New Chat')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_chat_sessions'
        ordering = ['-updated_at']

    def __str__(self):
        return f'Session #{self.pk} – {self.user} – {self.title}'


class AIChatMessage(models.Model):
    """Stores a single turn (human or AI) within a chat session."""

    ROLE_CHOICES = [
        ('human', 'Human'),
        ('ai', 'AI'),
    ]

    session = models.ForeignKey(
        AIChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    # Stores the last SQL query executed by the agent for audit purposes.
    # Not exposed in public API responses.
    generated_sql = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_chat_messages'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.role.upper()} – Session #{self.session_id}'
