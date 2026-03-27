from django.contrib import admin
from .models import AIChatSession, AIChatMessage


class AIChatMessageInline(admin.TabularInline):
    model = AIChatMessage
    fields = ('role', 'content', 'generated_sql', 'created_at')
    readonly_fields = ('created_at',)
    extra = 0


@admin.register(AIChatSession)
class AIChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__first_name', 'title')
    inlines = [AIChatMessageInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content',)
    readonly_fields = ('created_at',)
