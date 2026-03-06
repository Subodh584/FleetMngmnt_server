from django.contrib import admin

from .models import Message, Notification, SOSAlert


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'receiver', 'trip', 'is_read', 'sent_at']
    list_filter = ['is_read']
    raw_id_fields = ['sender', 'receiver', 'trip']
    search_fields = ['content']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'alert_type', 'title', 'status', 'created_at']
    list_filter = ['alert_type', 'status']
    raw_id_fields = ['user']
    search_fields = ['title', 'body']


@admin.register(SOSAlert)
class SOSAlertAdmin(admin.ModelAdmin):
    list_display = ['id', 'driver', 'vehicle', 'trip', 'resolved', 'triggered_at']
    list_filter = ['resolved']
    raw_id_fields = ['driver', 'vehicle', 'trip', 'resolved_by']
