from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class ChatRoom(models.Model):
    ROOM_TYPES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('protected', 'Password Protected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='public')
    password = models.CharField(max_length=128, blank=True, null=True)  # Hashed password for protected rooms
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    max_participants = models.PositiveIntegerField(default=100)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Chat Room"
        verbose_name_plural = "Chat Rooms"
    
    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"
    
    @property
    def participant_count(self):
        return self.participants.filter(is_active=True).count()
    
    @property
    def is_full(self):
        return self.participant_count >= self.max_participants


class ChatParticipant(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_participations')
    joined_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_moderator = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['room', 'user']
        verbose_name = "Chat Participant"
        verbose_name_plural = "Chat Participants"
    
    def __str__(self):
        return f"{self.user.username} in {self.room.name}"


class ChatMessage(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('system', 'System'),
        ('join', 'User Joined'),
        ('leave', 'User Left'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', null=True, blank=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
    
    def __str__(self):
        sender_name = self.sender.username if self.sender else "System"
        return f"{sender_name} in {self.room.name}: {self.content[:50]}..."


class ChatRoomInvite(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='invites')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invites')
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invites')
    created_at = models.DateTimeField(default=timezone.now)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    class Meta:
        unique_together = ['room', 'invited_user']
        verbose_name = "Chat Room Invite"
        verbose_name_plural = "Chat Room Invites"
    
    def __str__(self):
        return f"Invite to {self.room.name} for {self.invited_user.username}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at