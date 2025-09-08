from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta
from .models import ChatRoom, ChatMessage, ChatParticipant, ChatRoomInvite


class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name')


class ChatRoomListSerializer(serializers.ModelSerializer):
    created_by = UserBasicSerializer(read_only=True)
    participant_count = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    is_member = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = (
            'id', 'name', 'description', 'room_type', 'created_by', 
            'created_at', 'participant_count', 'max_participants', 
            'is_full', 'is_member'
        )
    
    def get_is_member(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.participants.filter(
                user=request.user, 
                is_active=True
            ).exists()
        return False


class ChatRoomCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    room_type = serializers.ChoiceField(choices=['public', 'private', 'protected'], default='public')
    password = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    max_participants = serializers.IntegerField(default=100, min_value=2, max_value=1000)
    
    def validate(self, data):
        room_type = data.get('room_type', 'public')
        password = data.get('password')
        
        if room_type == 'protected':
            if not password or not str(password).strip():
                raise serializers.ValidationError({"password": "Password is required for protected rooms."})
        
        # Ensure name is not empty
        name = data.get('name', '').strip()
        if not name:
            raise serializers.ValidationError({"name": "Room name is required."})
        
        return data
    
    def create(self, validated_data):
        from .models import ChatParticipant, ChatMessage
        
        # Clean the data
        name = validated_data['name'].strip()
        description = validated_data.get('description', '').strip()
        room_type = validated_data.get('room_type', 'public')
        password = validated_data.get('password')
        max_participants = validated_data.get('max_participants', 100)
        user = self.context['request'].user
        
        # Handle password
        hashed_password = None
        if password and str(password).strip():
            hashed_password = make_password(str(password).strip())
        
        # Create the room
        room = ChatRoom.objects.create(
            name=name,
            description=description,
            room_type=room_type,
            password=hashed_password,
            max_participants=max_participants,
            created_by=user
        )
        
        # Automatically add the creator as a participant and moderator
        ChatParticipant.objects.create(
            room=room,
            user=user,
            is_active=True,
            is_moderator=True
        )
        
        # Create welcome message
        ChatMessage.objects.create(
            room=room,
            message_type='system',
            content=f'Room "{room.name}" created by {user.username}'
        )
        
        return room
    
    def to_representation(self, instance):
        # Return the room data using the detail serializer
        return ChatRoomDetailSerializer(instance, context=self.context).data


class ChatRoomDetailSerializer(serializers.ModelSerializer):
    created_by = UserBasicSerializer(read_only=True)
    participant_count = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    participants = serializers.SerializerMethodField()
    recent_messages = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = (
            'id', 'name', 'description', 'room_type', 'created_by',
            'created_at', 'participant_count', 'max_participants',
            'is_full', 'participants', 'recent_messages'
        )
    
    def get_participants(self, obj):
        active_participants = obj.participants.filter(is_active=True).select_related('user')
        return [{
            'user': UserBasicSerializer(p.user).data,
            'joined_at': p.joined_at,
            'is_moderator': p.is_moderator,
            'last_seen': p.last_seen
        } for p in active_participants]
    
    def get_recent_messages(self, obj):
        recent_messages = obj.messages.select_related('sender').order_by('-timestamp')[:20]
        return ChatMessageSerializer(recent_messages, many=True).data


class ChatParticipantSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = ChatParticipant
        fields = ('user', 'joined_at', 'is_moderator', 'last_seen')


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = (
            'id', 'sender', 'message_type', 'content', 
            'timestamp', 'is_edited', 'edited_at'
        )


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('content',)
    
    def create(self, validated_data):
        validated_data['room'] = self.context['room']
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class JoinRoomSerializer(serializers.Serializer):
    password = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        room = self.context['room']
        user = self.context['request'].user
        
        # Check if room is full
        if room.is_full:
            raise serializers.ValidationError("Room is full.")
        
        # Check if user is already a participant
        if room.participants.filter(user=user, is_active=True).exists():
            raise serializers.ValidationError("You are already in this room.")
        
        # Check password for protected rooms
        if room.room_type == 'protected':
            password = data.get('password')
            if not password:
                raise serializers.ValidationError("Password is required for this room.")
            if not check_password(password, room.password):
                raise serializers.ValidationError("Invalid password.")
        
        # Check if room is private and user has invite
        if room.room_type == 'private':
            invite = ChatRoomInvite.objects.filter(
                room=room,
                invited_user=user,
                is_used=False,
                expires_at__gt=timezone.now()
            ).first()
            if not invite:
                raise serializers.ValidationError("You need an invitation to join this private room.")
            # Mark invite as used
            invite.is_used = True
            invite.save()
        
        return data


class ChatRoomInviteSerializer(serializers.ModelSerializer):
    invited_by = UserBasicSerializer(read_only=True)
    invited_user = UserBasicSerializer(read_only=True)
    room = ChatRoomListSerializer(read_only=True)
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = ChatRoomInvite
        fields = (
            'room', 'invited_by', 'invited_user', 
            'created_at', 'expires_at', 'is_used', 'is_expired'
        )


class CreateInviteSerializer(serializers.Serializer):
    username = serializers.CharField()
    expires_in_hours = serializers.IntegerField(default=24, min_value=1, max_value=168)  # Max 7 days
    
    def validate_username(self, value):
        try:
            user = User.objects.get(username=value)
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
    
    def create(self, validated_data):
        room = self.context['room']
        invited_by = self.context['request'].user
        invited_user = validated_data['username']
        expires_in_hours = validated_data['expires_in_hours']
        
        # Check if invite already exists
        existing_invite = ChatRoomInvite.objects.filter(
            room=room,
            invited_user=invited_user,
            is_used=False,
            expires_at__gt=timezone.now()
        ).first()
        
        if existing_invite:
            raise serializers.ValidationError("An active invitation already exists for this user.")
        
        invite = ChatRoomInvite.objects.create(
            room=room,
            invited_by=invited_by,
            invited_user=invited_user,
            expires_at=timezone.now() + timedelta(hours=expires_in_hours)
        )
        
        return invite
