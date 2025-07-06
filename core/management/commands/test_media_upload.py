from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from chat.models import Conversation, Message
from accounts.models import UserProfile
from chat.views import send_message
import os
import tempfile
from PIL import Image
import io

class Command(BaseCommand):
    help = 'Test media upload functionality by creating test files and sending messages'

    def handle(self, *args, **options):
        self.stdout.write('Testing media upload functionality...')
        
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
        
        # Get or create conversation between the two users
        conversation = Conversation.objects.filter(
            participants=user1
        ).filter(
            participants=user2
        ).first()
        
        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(user1, user2)
            self.stdout.write('Created new conversation')
        else:
            self.stdout.write('Using existing conversation')
        
        self.stdout.write(f'Conversation ID: {conversation.id}')
        
        # Create test image file
        self.stdout.write('\n--- Creating test image file ---')
        test_image_path = self.create_test_image()
        self.stdout.write(f'Created test image: {test_image_path}')
        
        # Test sending image message
        self.stdout.write('\n--- Testing image upload ---')
        self.test_image_upload(user1, conversation, test_image_path)
        
        # Create test video file
        self.stdout.write('\n--- Creating test video file ---')
        test_video_path = self.create_test_video()
        self.stdout.write(f'Created test video: {test_video_path}')
        
        # Test sending video message
        self.stdout.write('\n--- Testing video upload ---')
        self.test_video_upload(user1, conversation, test_video_path)
        
        # Test file size validation
        self.stdout.write('\n--- Testing file size validation ---')
        self.test_file_size_validation(user1, conversation)
        
        # Test file type validation
        self.stdout.write('\n--- Testing file type validation ---')
        self.test_file_type_validation(user1, conversation)
        
        # Clean up test files
        self.stdout.write('\n--- Cleaning up test files ---')
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
            self.stdout.write('Removed test image file')
        
        if os.path.exists(test_video_path):
            os.remove(test_video_path)
            self.stdout.write('Removed test video file')
        
        self.stdout.write('\nTest completed!')
    
    def create_test_image(self):
        """Create a simple test image file"""
        # Create a simple 100x100 red image
        img = Image.new('RGB', (100, 100), color='red')
        
        # Save to temporary file
        temp_dir = tempfile.gettempdir()
        image_path = os.path.join(temp_dir, 'test_image.jpg')
        
        img.save(image_path, 'JPEG')
        return image_path
    
    def create_test_video(self):
        """Create a simple test video file (actually just a text file with .mp4 extension)"""
        temp_dir = tempfile.gettempdir()
        video_path = os.path.join(temp_dir, 'test_video.mp4')
        
        # Create a dummy video file (just for testing)
        with open(video_path, 'w') as f:
            f.write('This is a dummy video file for testing purposes.')
        
        return video_path
    
    def create_request(self, user, method='POST', **kwargs):
        """Create a test request with proper middleware"""
        factory = RequestFactory()
        request = factory.post('/chat/send_message/', **kwargs)
        
        # Add middleware
        SessionMiddleware(lambda req: None).process_request(request)
        AuthenticationMiddleware(lambda req: None).process_request(request)
        MessageMiddleware(lambda req: None).process_request(request)
        
        # Set user
        request.user = user
        
        return request
    
    def test_image_upload(self, user, conversation, image_path):
        """Test uploading an image file"""
        try:
            with open(image_path, 'rb') as f:
                request = self.create_request(
                    user,
                    data={
                        'conversation_id': conversation.id,
                        'content': 'Test image message'
                    },
                    files={'image': f}
                )
                
                response = send_message(request)
                
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS('✓ Image upload successful'))
                    # Check if message was created
                    message = Message.objects.filter(
                        conversation=conversation,
                        sender=user,
                        message_type='image'
                    ).first()
                    if message:
                        self.stdout.write(f'  Message ID: {message.id}')
                        self.stdout.write(f'  Image path: {message.image.path if message.image else "None"}')
                    else:
                        self.stdout.write(self.style.WARNING('  Warning: Message not found in database'))
                else:
                    self.stdout.write(self.style.ERROR(f'✗ Image upload failed: {response.status_code}'))
                    self.stdout.write(f'  Response: {response.content.decode()}')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Image upload error: {e}'))
    
    def test_video_upload(self, user, conversation, video_path):
        """Test uploading a video file"""
        try:
            with open(video_path, 'rb') as f:
                request = self.create_request(
                    user,
                    data={
                        'conversation_id': conversation.id,
                        'content': 'Test video message'
                    },
                    files={'video': f}
                )
                
                response = send_message(request)
                
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS('✓ Video upload successful'))
                    # Check if message was created
                    message = Message.objects.filter(
                        conversation=conversation,
                        sender=user,
                        message_type='video'
                    ).first()
                    if message:
                        self.stdout.write(f'  Message ID: {message.id}')
                        self.stdout.write(f'  Video path: {message.video.path if message.video else "None"}')
                    else:
                        self.stdout.write(self.style.WARNING('  Warning: Message not found in database'))
                else:
                    self.stdout.write(self.style.ERROR(f'✗ Video upload failed: {response.status_code}'))
                    self.stdout.write(f'  Response: {response.content.decode()}')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Video upload error: {e}'))
    
    def test_file_size_validation(self, user, conversation):
        """Test file size validation"""
        # Create a large file (over 10MB)
        temp_dir = tempfile.gettempdir()
        large_file_path = os.path.join(temp_dir, 'large_file.jpg')
        
        # Create a file larger than 10MB
        with open(large_file_path, 'wb') as f:
            f.write(b'0' * (11 * 1024 * 1024))  # 11MB
        
        try:
            with open(large_file_path, 'rb') as f:
                request = self.create_request(
                    user,
                    data={
                        'conversation_id': conversation.id,
                        'content': 'Large file test'
                    },
                    files={'image': f}
                )
                
                response = send_message(request)
                
                if response.status_code == 200:
                    response_data = response.json()
                    if not response_data.get('success'):
                        self.stdout.write(self.style.SUCCESS('✓ File size validation working (rejected large file)'))
                        self.stdout.write(f'  Error message: {response_data.get("message")}')
                    else:
                        self.stdout.write(self.style.ERROR('✗ File size validation failed (accepted large file)'))
                else:
                    self.stdout.write(self.style.ERROR(f'✗ File size validation test failed: {response.status_code}'))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ File size validation test error: {e}'))
        finally:
            if os.path.exists(large_file_path):
                os.remove(large_file_path)
    
    def test_file_type_validation(self, user, conversation):
        """Test file type validation"""
        # Create a text file (not an image or video)
        temp_dir = tempfile.gettempdir()
        text_file_path = os.path.join(temp_dir, 'test.txt')
        
        with open(text_file_path, 'w') as f:
            f.write('This is a text file, not an image or video.')
        
        try:
            with open(text_file_path, 'rb') as f:
                request = self.create_request(
                    user,
                    data={
                        'conversation_id': conversation.id,
                        'content': 'Text file test'
                    },
                    files={'image': f}
                )
                
                response = send_message(request)
                
                if response.status_code == 200:
                    response_data = response.json()
                    if not response_data.get('success'):
                        self.stdout.write(self.style.SUCCESS('✓ File type validation working (rejected text file)'))
                        self.stdout.write(f'  Error message: {response_data.get("message")}')
                    else:
                        self.stdout.write(self.style.ERROR('✗ File type validation failed (accepted text file)'))
                else:
                    self.stdout.write(self.style.ERROR(f'✗ File type validation test failed: {response.status_code}'))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ File type validation test error: {e}'))
        finally:
            if os.path.exists(text_file_path):
                os.remove(text_file_path) 