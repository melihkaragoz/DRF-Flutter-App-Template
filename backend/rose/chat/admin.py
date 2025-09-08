from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import ChatRoom, ChatMessage, ChatParticipant, ChatRoomInvite


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_type', 'created_by', 'participant_count', 'is_active', 'created_at')
    list_filter = ('room_type', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'created_by__username')
    readonly_fields = ('id', 'created_at', 'participant_count')
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'description', 'room_type')
        }),
        ('Security', {
            'fields': ('password', 'max_participants')
        }),
        ('Meta', {
            'fields': ('created_by', 'created_at', 'is_active')
        }),
    )


@admin.register(ChatParticipant)
class ChatParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'is_active', 'is_moderator', 'joined_at', 'last_seen')
    list_filter = ('is_active', 'is_moderator', 'joined_at')
    search_fields = ('user__username', 'room__name')
    readonly_fields = ('joined_at',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'room', 'message_type', 'content_preview', 'timestamp', 'is_edited')
    list_filter = ('message_type', 'is_edited', 'timestamp')
    search_fields = ('sender__username', 'room__name', 'content')
    readonly_fields = ('id', 'timestamp', 'edited_at')
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'


@admin.register(ChatRoomInvite)
class ChatRoomInviteAdmin(admin.ModelAdmin):
    list_display = ('room', 'invited_user', 'invited_by', 'is_used', 'is_expired', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('room__name', 'invited_user__username', 'invited_by__username')
    readonly_fields = ('created_at', 'is_expired')


# Extend User admin to show chat permissions
class ChatUserAdmin(BaseUserAdmin):
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            # Add chat permissions to user permissions
            fieldsets = list(fieldsets)
            for i, (name, options) in enumerate(fieldsets):
                if name == 'Permissions':
                    fields = list(options.get('fields', ()))
                    if 'user_permissions' in fields:
                        # Chat permissions will be shown in user_permissions
                        pass
        return fieldsets


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, ChatUserAdmin)