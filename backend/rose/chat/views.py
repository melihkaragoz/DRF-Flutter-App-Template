from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from .models import ChatRoom, ChatMessage, ChatParticipant, ChatRoomInvite
from .serializers import (
    ChatRoomListSerializer, ChatRoomCreateSerializer, ChatRoomDetailSerializer,
    ChatMessageSerializer, ChatMessageCreateSerializer, JoinRoomSerializer,
    ChatRoomInviteSerializer, CreateInviteSerializer
)


class ChatMessagePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class HasChatAdminPermission(permissions.BasePermission):
    """Custom permission to check if user has chat_admin permission"""
    
    def has_permission(self, request, view):
        # For now, allow all authenticated users to create rooms
        # TODO: Implement proper chat_admin permission checking
        return request.user.is_authenticated


class ChatRoomViewSet(ModelViewSet):
    queryset = ChatRoom.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        # Add debug logging
        print("CREATE ROOM REQUEST DATA:", request.data)
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            print("CREATE ROOM ERROR:", str(e))
            return Response(
                {'error': f'Failed to create room: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ChatRoomCreateSerializer
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return ChatRoomDetailSerializer
        return ChatRoomListSerializer
    
    def get_permissions(self):
        """Only users with chat_admin permission can create rooms"""
        if self.action == 'create':
            permission_classes = [HasChatAdminPermission]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter based on search query
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        # Filter by room type
        room_type = self.request.query_params.get('room_type', '')
        if room_type:
            queryset = queryset.filter(room_type=room_type)
        
        # Show only public rooms for non-members, unless they're the creator
        user = self.request.user
        if self.action == 'list':
            # For list view, show public rooms and private rooms the user created or is invited to
            queryset = queryset.filter(
                Q(room_type='public') |
                Q(room_type='protected') |
                Q(created_by=user) |
                Q(participants__user=user, participants__is_active=True) |
                Q(invites__invited_user=user, invites__is_used=False, invites__expires_at__gt=timezone.now())
            ).distinct()
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a chat room"""
        room = self.get_object()
        serializer = JoinRoomSerializer(
            data=request.data,
            context={'room': room, 'request': request}
        )
        
        if serializer.is_valid():
            # Create or reactivate participant
            participant, created = ChatParticipant.objects.get_or_create(
                room=room,
                user=request.user,
                defaults={'is_active': True}
            )
            
            if not created and not participant.is_active:
                participant.is_active = True
                participant.joined_at = timezone.now()
                participant.save()
            
            # Create system message
            ChatMessage.objects.create(
                room=room,
                message_type='join',
                content=f"{request.user.username} joined the room"
            )
            
            return Response({
                'message': 'Successfully joined the room',
                'room': ChatRoomDetailSerializer(room, context={'request': request}).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a chat room"""
        room = self.get_object()
        
        try:
            participant = ChatParticipant.objects.get(
                room=room,
                user=request.user,
                is_active=True
            )
            participant.is_active = False
            participant.save()
            
            # Create system message
            ChatMessage.objects.create(
                room=room,
                message_type='leave',
                content=f"{request.user.username} left the room"
            )
            
            return Response({'message': 'Successfully left the room'})
        
        except ChatParticipant.DoesNotExist:
            return Response(
                {'error': 'You are not a member of this room'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get messages for a chat room"""
        room = self.get_object()
        
        # Check if user is a participant
        if not room.participants.filter(user=request.user, is_active=True).exists():
            return Response(
                {'error': 'You must be a member of this room to view messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        messages = room.messages.select_related('sender').order_by('-timestamp')
        paginator = ChatMessagePagination()
        page = paginator.paginate_queryset(messages, request)
        
        if page is not None:
            serializer = ChatMessageSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message to a chat room"""
        room = self.get_object()
        
        # Check if user is a participant
        if not room.participants.filter(user=request.user, is_active=True).exists():
            return Response(
                {'error': 'You must be a member of this room to send messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ChatMessageCreateSerializer(
            data=request.data,
            context={'room': room, 'request': request}
        )
        
        if serializer.is_valid():
            message = serializer.save()
            return Response(
                ChatMessageSerializer(message).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[HasChatAdminPermission])
    def invite_user(self, request, pk=None):
        """Invite a user to a private room"""
        room = self.get_object()
        
        # Only room creator or moderators can invite
        if (room.created_by != request.user and 
            not room.participants.filter(user=request.user, is_moderator=True).exists()):
            return Response(
                {'error': 'Only room creator or moderators can invite users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CreateInviteSerializer(
            data=request.data,
            context={'room': room, 'request': request}
        )
        
        if serializer.is_valid():
            invite = serializer.save()
            return Response(
                ChatRoomInviteSerializer(invite).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_invites(request):
    """Get current user's pending invites"""
    invites = ChatRoomInvite.objects.filter(
        invited_user=request.user,
        is_used=False,
        expires_at__gt=timezone.now()
    ).select_related('room', 'invited_by')
    
    serializer = ChatRoomInviteSerializer(invites, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_rooms(request):
    """Get rooms where user is a participant"""
    user_rooms = ChatRoom.objects.filter(
        participants__user=request.user,
        participants__is_active=True,
        is_active=True
    ).distinct().order_by('-participants__last_seen')
    
    serializer = ChatRoomListSerializer(
        user_rooms, 
        many=True, 
        context={'request': request}
    )
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def join_room_by_id(request):
    """Join a room by its ID (for private rooms)"""
    room_id = request.data.get('room_id')
    password = request.data.get('password', '')
    
    if not room_id:
        return Response(
            {'error': 'room_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        room = ChatRoom.objects.get(id=room_id, is_active=True)
    except ChatRoom.DoesNotExist:
        return Response(
            {'error': 'Room not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = JoinRoomSerializer(
        data={'password': password},
        context={'room': room, 'request': request}
    )
    
    if serializer.is_valid():
        # Create or reactivate participant
        participant, created = ChatParticipant.objects.get_or_create(
            room=room,
            user=request.user,
            defaults={'is_active': True}
        )
        
        if not created and not participant.is_active:
            participant.is_active = True
            participant.joined_at = timezone.now()
            participant.save()
        
        # Create system message
        ChatMessage.objects.create(
            room=room,
            message_type='join',
            content=f"{request.user.username} joined the room"
        )
        
        return Response({
            'message': 'Successfully joined the room',
            'room': ChatRoomDetailSerializer(room, context={'request': request}).data
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)