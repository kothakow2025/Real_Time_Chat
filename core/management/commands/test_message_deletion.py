from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from chat.models import Conversation, Message
from accounts.models import UserProfile
import os

class Command(BaseCommand):
    help = 'Test the message deletion functionality with media files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion of all messages older than 24 hours',
        )

    def handle(self, *args, **options):
        self.stdout.write('Testing message deletion functionality...')
        
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
        
        # Ensure user profiles exist
        try:
            profile1, created = UserProfile.objects.get_or_create(user=user1)
            if created:
                self.stdout.write(f'Created profile for {user1.username}')
        except Exception as e:
            self.stdout.write(f'Error creating profile for {user1.username}: {e}')
            profile1 = user1.userprofile
        
        try:
            profile2, created = UserProfile.objects.get_or_create(user=user2)
            if created:
                self.stdout.write(f'Created profile for {user2.username}')
        except Exception as e:
            self.stdout.write(f'Error creating profile for {user2.username}: {e}')
            profile2 = user2.userprofile
        
        # Create conversation
        conversation, created = Conversation.objects.get_or_create()
        if created:
            conversation.participants.add(user1, user2)
            self.stdout.write('Created conversation')
        
        # Create test messages with different timestamps
        messages_created = []
        
        # Message 1: Recent (should not be deleted)
        message1 = Message.objects.create(
            conversation=conversation,
            sender=user1,
            message_type='text',
            content='This is a recent message that should not be deleted.',
            timestamp=timezone.now() - timedelta(hours=12)  # 12 hours ago
        )
        messages_created.append(message1)
        self.stdout.write('Created recent message (12 hours ago)')
        
        # Message 2: Old text message (should be deleted)
        message2 = Message.objects.create(
            conversation=conversation,
            sender=user2,
            message_type='text',
            content='This is an old text message that should be deleted.',
            timestamp=timezone.now() - timedelta(hours=25)  # 25 hours ago
        )
        messages_created.append(message2)
        self.stdout.write('Created old text message (25 hours ago)')
        
        # Message 3: Old message with image (should be deleted)
        message3 = Message.objects.create(
            conversation=conversation,
            sender=user1,
            message_type='image',
            content='This is an old image message that should be deleted.',
            timestamp=timezone.now() - timedelta(hours=26)  # 26 hours ago
        )
        messages_created.append(message3)
        self.stdout.write('Created old image message (26 hours ago)')
        
        # Message 4: Old message with video (should be deleted)
        message4 = Message.objects.create(
            conversation=conversation,
            sender=user2,
            message_type='video',
            content='This is an old video message that should be deleted.',
            timestamp=timezone.now() - timedelta(hours=27)  # 27 hours ago
        )
        messages_created.append(message4)
        self.stdout.write('Created old video message (27 hours ago)')
        
        # Create dummy media files for testing
        media_dir = 'media/chat_media'
        images_dir = f'{media_dir}/images'
        videos_dir = f'{media_dir}/videos'
        
        # Create directories if they don't exist
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(videos_dir, exist_ok=True)
        
        # Create dummy image file
        image_path = f'{images_dir}/test_image_{message3.id}.jpg'
        with open(image_path, 'w') as f:
            f.write('dummy image content')
        
        # Create dummy video file
        video_path = f'{videos_dir}/test_video_{message4.id}.mp4'
        with open(video_path, 'w') as f:
            f.write('dummy video content')
        
        # Update message records to point to the dummy files
        message3.image = f'chat_media/images/test_image_{message3.id}.jpg'
        message3.save()
        
        message4.video = f'chat_media/videos/test_video_{message4.id}.mp4'
        message4.save()
        
        self.stdout.write(f'Created dummy media files: {image_path}, {video_path}')
        
        # Test the should_be_deleted method
        self.stdout.write('\n--- Testing should_be_deleted method ---')
        for message in messages_created:
            should_delete = message.should_be_deleted()
            self.stdout.write(f'Message {message.id} ({message.timestamp}): should_be_deleted = {should_delete}')
        
        # Test manual deletion of old messages
        self.stdout.write('\n--- Testing manual deletion ---')
        old_messages = [msg for msg in messages_created if msg.should_be_deleted()]
        self.stdout.write(f'Found {len(old_messages)} old messages to delete')
        
        for message in old_messages:
            try:
                self.stdout.write(f'Deleting message {message.id}...')
                message.delete_with_media()
                self.stdout.write(self.style.SUCCESS(f'Successfully deleted message {message.id}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error deleting message {message.id}: {e}'))
        
        # Verify deletion
        self.stdout.write('\n--- Verification ---')
        remaining_messages = Message.objects.filter(conversation=conversation)
        self.stdout.write(f'Remaining messages: {remaining_messages.count()}')
        
        for message in remaining_messages:
            self.stdout.write(f'Message {message.id}: {message.content[:50]}... ({message.timestamp})')
        
        # Check if media files were deleted
        self.stdout.write('\n--- Media file verification ---')
        if os.path.exists(image_path):
            self.stdout.write(self.style.WARNING(f'Image file still exists: {image_path}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Image file successfully deleted: {image_path}'))
        
        if os.path.exists(video_path):
            self.stdout.write(self.style.WARNING(f'Video file still exists: {video_path}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Video file successfully deleted: {video_path}'))
        
        # Test the Celery task
        self.stdout.write('\n--- Testing Celery task ---')
        try:
            from core.tasks import delete_expired_messages
            result = delete_expired_messages()
            self.stdout.write(self.style.SUCCESS(f'Celery task result: {result}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error running Celery task: {e}'))
        
        self.stdout.write('\nTest completed!') 