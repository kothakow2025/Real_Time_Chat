from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import FriendRequest
from chat.models import Conversation, Message
import os

class Command(BaseCommand):
    help = 'Test the unfriend functionality'

    def handle(self, *args, **options):
        self.stdout.write('Testing unfriend functionality...')
        
        # Create test users if they don't exist
        user1, created = User.objects.get_or_create(
            username='testuser1',
            defaults={'email': 'test1@example.com', 'first_name': 'Test', 'last_name': 'User1'}
        )
        if created:
            self.stdout.write(f'Created test user: {user1.username}')
        
        user2, created = User.objects.get_or_create(
            username='testuser2',
            defaults={'email': 'test2@example.com', 'first_name': 'Test', 'last_name': 'User2'}
        )
        if created:
            self.stdout.write(f'Created test user: {user2.username}')
        
        # Create friend request
        friend_request, created = FriendRequest.objects.get_or_create(
            from_user=user1,
            to_user=user2,
            defaults={'status': 'accepted'}
        )
        if created:
            self.stdout.write('Created friend request')
        
        # Create conversation
        conversation, created = Conversation.objects.get_or_create()
        if created:
            conversation.participants.add(user1, user2)
            self.stdout.write('Created conversation')
        
        # Create test messages
        message1 = Message.objects.create(
            conversation=conversation,
            sender=user1,
            message_type='text',
            content='Hello from user1!'
        )
        self.stdout.write('Created text message')
        
        message2 = Message.objects.create(
            conversation=conversation,
            sender=user2,
            message_type='text',
            content='Hello from user2!'
        )
        self.stdout.write('Created text message')
        
        # Test unfriend functionality
        self.stdout.write('Testing unfriend...')
        
        # Import the unfriend function
        from accounts.views import unfriend_user
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser
        from django.http import JsonResponse
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.post('/unfriend/', {'user_id': user2.id})
        request.user = user1
        
        # Call the unfriend function
        response = unfriend_user(request)
        
        if response.status_code == 200:
            self.stdout.write(self.style.SUCCESS('Unfriend test passed!'))
            
            # Verify that friend request is deleted
            if not FriendRequest.objects.filter(
                from_user=user1, to_user=user2, status='accepted'
            ).exists():
                self.stdout.write(self.style.SUCCESS('Friend request deleted successfully'))
            else:
                self.stdout.write(self.style.ERROR('Friend request still exists'))
            
            # Verify that conversation is deleted
            if not Conversation.objects.filter(participants=user1).filter(participants=user2).exists():
                self.stdout.write(self.style.SUCCESS('Conversation deleted successfully'))
            else:
                self.stdout.write(self.style.ERROR('Conversation still exists'))
            
            # Verify that messages are deleted
            if not Message.objects.filter(conversation=conversation).exists():
                self.stdout.write(self.style.SUCCESS('Messages deleted successfully'))
            else:
                self.stdout.write(self.style.ERROR('Messages still exist'))
                
        else:
            self.stdout.write(self.style.ERROR(f'Unfriend test failed with status: {response.status_code}'))
        
        self.stdout.write('Test completed!') 