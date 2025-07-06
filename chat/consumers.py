import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Conversation, Message, MessageReadStatus
from accounts.models import UserProfile
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        
        # AUTH CHECK: Only allow authenticated users
        if not self.scope['user'].is_authenticated:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Update user online status
        await self.update_user_online_status(self.scope['user'], True)
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Update user online status
        if self.scope['user'].is_authenticated:
            await self.update_user_online_status(self.scope['user'], False)
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')

        if message_type == 'chat_message':
            message_data = text_data_json.get('message', {})
            content = message_data.get('content', '').strip()

            if not content:
                return  # Ignore empty messages

            # Save the message to the database
            message = await self.save_message(
                self.scope['user'],
                self.conversation_id,
                content
            )
            
            profile = await self.get_user_profile(self.scope['user'])
            profile_picture_url = profile.get_profile_picture_url() if profile else ''

            # Construct the full message payload, consistent with the view
            full_message_payload = {
                'id': message.id,
                'sender_id': self.scope['user'].id,
                'sender_username': self.scope['user'].username,
                'sender_profile_picture_url': profile_picture_url,
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'image_url': None,  # Text messages from consumer don't have images
                'video_url': None,
                'is_edited': message.is_edited,
                'is_unsent': message.is_unsent,
                'edited_at': message.edited_at.isoformat() if message.edited_at else None,
            }

            # Send the complete message payload to the room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': full_message_payload
                }
            )
        elif message_type == 'edit_message':
            message_data = text_data_json.get('message', {})
            message_id = message_data.get('id')
            new_content = message_data.get('content', '').strip()
            
            if message_id and new_content:
                success = await self.edit_message(message_id, self.scope['user'], new_content)
                if success:
                    # Broadcast the edit to all users in the room
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'message_edited',
                            'message': {
                                'id': message_id,
                                'content': new_content,
                                'is_edited': True,
                                'edited_at': timezone.now().isoformat(),
                            }
                        }
                    )
        elif message_type == 'unsend_message':
            message_data = text_data_json.get('message', {})
            message_id = message_data.get('id')
            
            if message_id:
                success = await self.unsend_message(message_id, self.scope['user'])
                if success:
                    # Broadcast the unsend to all users in the room
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'message_unsent',
                            'message': {
                                'id': message_id,
                                'is_unsent': True,
                            }
                        }
                    )
        elif message_type == 'mark_read':
            message_id = text_data_json.get('message_id')
            if message_id:
                await self.mark_message_read(message_id, self.scope['user'])
        elif message_type == 'typing':
            # Broadcast typing indicator to other users in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_typing',
                    'username': self.scope['user'].username
                }
            )
        elif message_type == 'stop_typing':
            # Broadcast stop typing indicator to other users in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_stop_typing'
                }
            )
    
    async def chat_message(self, event):
        # This handler receives messages from the group and sends them to the client.
        message_payload = event['message']

        # Send the standardized message payload to the WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message_payload
        }))
    
    async def message_edited(self, event):
        # Send message edit notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message': event['message']
        }))
    
    async def message_unsent(self, event):
        # Send message unsend notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message_unsent',
            'message': event['message']
        }))
    
    async def user_typing(self, event):
        # Send typing indicator to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'username': event['username']
        }))
    
    async def user_stop_typing(self, event):
        # Send stop typing indicator to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'stop_typing'
        }))
    
    @database_sync_to_async
    def save_message(self, user, conversation_id, content):
        conversation = Conversation.objects.get(id=conversation_id)
        message = Message.objects.create(
            conversation=conversation,
            sender=user,
            content=content
        )
        return message
    
    @database_sync_to_async
    def edit_message(self, message_id, user, new_content):
        try:
            message = Message.objects.get(id=message_id)
            if message.can_be_edited(user):
                message.edit_message(new_content)
                return True
            return False
        except Message.DoesNotExist:
            return False
    
    @database_sync_to_async
    def unsend_message(self, message_id, user):
        try:
            message = Message.objects.get(id=message_id)
            if message.can_be_unsent(user):
                message.unsend_message()
                return True
            return False
        except Message.DoesNotExist:
            return False
    
    @database_sync_to_async
    def mark_message_read(self, message_id, user):
        try:
            message = Message.objects.get(id=message_id)
            MessageReadStatus.objects.update_or_create(
                message=message,
                user=user,
                defaults={'is_read': True}
            )
        except Message.DoesNotExist:
            pass
    
    @database_sync_to_async
    def update_user_online_status(self, user, is_online):
        try:
            profile = user.userprofile
            profile.is_online = is_online
            profile.last_seen = timezone.now()
            profile.save()
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=user, is_online=is_online)

    @database_sync_to_async
    def get_user_profile(self, user):
        try:
            return user.userprofile
        except UserProfile.DoesNotExist:
            return None

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope['user'].is_authenticated:
            self.user_group_name = f'notifications_{self.scope["user"].id}'
            
            # Join user group
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            
            await self.accept()
        else:
            await self.close()
    
    async def disconnect(self, close_code):
        if self.scope['user'].is_authenticated:
            # Leave user group
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
    
    async def friend_request_notification(self, event):
        # Send friend request notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'friend_request',
            'from_user': event['from_user'],
            'message': event['message']
        }))
    
    async def new_message_notification(self, event):
        # Send new message notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'from_user': event['from_user'],
            'conversation_id': event['conversation_id'],
            'message': event['message']
        }))
    
    async def send_notification(self, event):
        # Send generic notification to WebSocket
        await self.send(text_data=json.dumps(event['notification']))