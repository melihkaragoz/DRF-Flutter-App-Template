import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .models import ChatRoom, ChatMessage, ChatParticipant
from .serializers import ChatMessageSerializer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = None
        
        # Authenticate user
        token = self.scope.get('query_string', b'').decode('utf-8')
        if token.startswith('token='):
            token = token.split('token=')[1]
            self.user = await self.authenticate_user(token)
        
        if not self.user:
            await self.close()
            return
        
        # Check if user can join this room
        can_join = await self.can_user_join_room()
        if not can_join:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Update user's last seen
        await self.update_last_seen()
        
        # Send user list to the room
        await self.send_user_list()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            # Update user's last seen
            await self.update_last_seen()
            
            # Send updated user list
            await self.send_user_list()
    
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'chat_message')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(text_data_json)
            elif message_type == 'typing':
                await self.handle_typing(text_data_json)
            elif message_type == 'ping':
                await self.handle_ping()
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
    
    async def handle_chat_message(self, data):
        message_content = data.get('message', '').strip()
        if not message_content:
            return
        
        # Save message to database
        message = await self.save_message(message_content)
        if not message:
            return
        
        # Serialize message
        message_data = await self.serialize_message(message)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_data
            }
        )
    
    async def handle_typing(self, data):
        is_typing = data.get('is_typing', False)
        
        # Send typing indicator to room group (except sender)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing,
                'sender_channel': self.channel_name
            }
        )
    
    async def handle_ping(self):
        await self.update_last_seen()
        await self.send(text_data=json.dumps({
            'type': 'pong'
        }))
    
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))
    
    async def typing_indicator(self, event):
        # Don't send typing indicator back to the sender
        if event.get('sender_channel') != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))
    
    async def user_list(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_list',
            'users': event['users']
        }))
    
    @database_sync_to_async
    def authenticate_user(self, token):
        try:
            # Validate JWT token
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            user = User.objects.get(id=user_id)
            return user
        except (InvalidToken, TokenError, User.DoesNotExist):
            return None
    
    @database_sync_to_async
    def can_user_join_room(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id, is_active=True)
            
            # Check if user is already a participant
            participant = ChatParticipant.objects.filter(
                room=room,
                user=self.user,
                is_active=True
            ).first()
            
            if participant is not None:
                return True
                
            # If user is the room creator, automatically add them as participant
            if room.created_by == self.user:
                ChatParticipant.objects.create(
                    room=room,
                    user=self.user,
                    is_active=True,
                    is_moderator=True
                )
                return True
                
            return False
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, content):
        try:
            room = ChatRoom.objects.get(id=self.room_id, is_active=True)
            
            # Check if user is still a participant
            participant = ChatParticipant.objects.filter(
                room=room,
                user=self.user,
                is_active=True
            ).first()
            
            if not participant:
                return None
            
            message = ChatMessage.objects.create(
                room=room,
                sender=self.user,
                content=content,
                message_type='text'
            )
            return message
        except ChatRoom.DoesNotExist:
            return None
    
    @database_sync_to_async
    def serialize_message(self, message):
        serializer = ChatMessageSerializer(message)
        return serializer.data
    
    @database_sync_to_async
    def update_last_seen(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id, is_active=True)
            ChatParticipant.objects.filter(
                room=room,
                user=self.user
            ).update(last_seen=timezone.now())
        except ChatRoom.DoesNotExist:
            pass
    
    @database_sync_to_async
    def get_active_users(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id, is_active=True)
            participants = ChatParticipant.objects.filter(
                room=room,
                is_active=True
            ).select_related('user').order_by('user__username')
            
            return [{
                'id': p.user.id,
                'username': p.user.username,
                'is_moderator': p.is_moderator,
                'last_seen': p.last_seen.isoformat() if p.last_seen else None
            } for p in participants]
        except ChatRoom.DoesNotExist:
            return []
    
    async def send_user_list(self):
        users = await self.get_active_users()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_list',
                'users': users
            }
        )
