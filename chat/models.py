from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import os

class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        participants_list = ", ".join([user.username for user in self.participants.all()])
        return f"Conversation: {participants_list}"
    
    def get_other_participant(self, user):
        return self.participants.exclude(id=user.id).first()
    
    def last_message(self):
        return self.messages.order_by('-timestamp').first()

class Message(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(blank=True, null=True)  # For text messages
    image = models.ImageField(upload_to='chat_media/images/', blank=True, null=True)
    video = models.FileField(upload_to='chat_media/videos/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_edited = models.BooleanField(default=False)
    is_unsent = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        if self.message_type == 'text':
            return f"{self.sender.username}: {self.content[:50]}..."
        else:
            return f"{self.sender.username}: [{self.message_type.upper()}]"
    
    def can_be_edited(self, user):
        """Check if user can edit this message"""
        # Only sender can edit, and only within 15 minutes of sending
        if self.sender != user:
            return False
        
        # Can't edit unsent messages
        if self.is_unsent:
            return False
        
        # Can only edit text messages
        if self.message_type != 'text':
            return False
        
        # Can only edit within 15 minutes
        time_limit = self.timestamp + timedelta(minutes=15)
        return timezone.now() <= time_limit
    
    def can_be_unsent(self, user):
        """Check if user can unsend this message"""
        # Only sender can unsend
        if self.sender != user:
            return False
        
        # Can't unsend already unsent messages
        if self.is_unsent:
            return False
        
        # Can unsend within 1 hour of sending
        time_limit = self.timestamp + timedelta(hours=1)
        return timezone.now() <= time_limit
    
    def edit_message(self, new_content):
        """Edit the message content"""
        if self.message_type != 'text':
            raise ValueError("Only text messages can be edited")
        
        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save()
    
    def unsend_message(self):
        """Mark message as unsent"""
        self.is_unsent = True
        self.save()
    
    def should_be_deleted(self):
        """Check if message should be deleted based on user's deletion settings"""
        deletion_hours = self.sender.userprofile.message_deletion_hours
        deletion_time = self.timestamp + timedelta(hours=deletion_hours)
        return timezone.now() > deletion_time
    
    def delete_with_media(self):
        """Delete message and associated media files if they exist"""
        try:
            # Delete image file if it exists
            if self.image:
                # Only use .delete() method of the storage backend (S3 or local)
                try:
                    self.image.delete(save=False)
                except Exception as e:
                    print(f"Error deleting image via storage: {e}")
            
            # Delete video file if it exists
            if self.video:
                # Only use .delete() method of the storage backend (S3 or local)
                try:
                    self.video.delete(save=False)
                except Exception as e:
                    print(f"Error deleting video via storage: {e}")
            
            # Delete the message (this will also delete MessageReadStatus due to CASCADE)
            self.delete()
            print(f"Successfully deleted message {self.id} with all media files")
            
        except Exception as e:
            print(f"Error in delete_with_media for message {self.id}: {e}")
            # Still try to delete the message even if media deletion fails
            self.delete()

class MessageReadStatus(models.Model):
    message = models.ForeignKey(Message, related_name='messagereadstatus', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=True)
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user')
    
    def __str__(self):
        return f"{self.user.username} read message at {self.read_at}"
