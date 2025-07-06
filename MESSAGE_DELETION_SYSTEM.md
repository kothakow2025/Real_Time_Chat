# Message Deletion System Documentation

## Overview
The chat application implements an automatic message deletion system that permanently removes messages and their associated media files after 24 hours (or a user-configurable time period). This ensures data privacy and storage efficiency.

## How It Works

### 1. **User Configuration**
- Each user has a `message_deletion_hours` setting in their UserProfile
- Default value: 24 hours
- Users can customize this setting in their profile settings

### 2. **Automatic Deletion Process**
- **Celery Task**: Runs every hour to check for expired messages
- **Deletion Criteria**: Messages older than the user's configured deletion time
- **Media Cleanup**: Both database records and physical files are deleted

### 3. **Media File Handling**
- **Images**: Stored in `media/chat_media/images/`
- **Videos**: Stored in `media/chat_media/videos/`
- **Deletion**: Physical files are removed from the file system

## Technical Implementation

### Message Model (`chat/models.py`)

#### `should_be_deleted()` Method
```python
def should_be_deleted(self):
    """Check if message should be deleted based on user's deletion settings"""
    deletion_hours = self.sender.userprofile.message_deletion_hours
    deletion_time = self.timestamp + timedelta(hours=deletion_hours)
    return timezone.now() > deletion_time
```

#### `delete_with_media()` Method
```python
def delete_with_media(self):
    """Delete message and associated media files if they exist"""
    try:
        # Delete image file if it exists
        if self.image:
            if hasattr(self.image, 'path') and os.path.exists(self.image.path):
                os.remove(self.image.path)
            # Also try to delete using storage if available
            self.image.delete(save=False)
        
        # Delete video file if it exists
        if self.video:
            if hasattr(self.video, 'path') and os.path.exists(self.video.path):
                os.remove(self.video.path)
            # Also try to delete using storage if available
            self.video.delete(save=False)
        
        # Delete the message (this will also delete MessageReadStatus due to CASCADE)
        self.delete()
        
    except Exception as e:
        # Still try to delete the message even if media deletion fails
        self.delete()
```

### Celery Task (`core/tasks.py`)

#### `delete_expired_messages()` Task
```python
@shared_task
def delete_expired_messages():
    """Delete messages that have exceeded their deletion time based on user settings"""
    logger.info("Starting expired message deletion task")
    deleted_count = 0
    error_count = 0
    
    # Get all messages that should be deleted
    messages = Message.objects.select_related('sender__userprofile').all()
    messages_to_delete = [msg for msg in messages if msg.should_be_deleted()]
    
    # Delete messages with their media files
    for message in messages_to_delete:
        try:
            message.delete_with_media()
            deleted_count += 1
            logger.info(f"Successfully deleted message {message.id} with media files")
        except Exception as e:
            error_count += 1
            logger.error(f"Error deleting message {message.id}: {str(e)}")
    
    return f"Deleted {deleted_count} expired messages, {error_count} errors"
```

### Celery Configuration (`kothakow/celery.py`)

#### Scheduled Tasks
```python
app.conf.beat_schedule = {
    'delete-expired-messages': {
        'task': 'core.tasks.delete_expired_messages',
        'schedule': 3600.0,  # Run every hour
    },
    'cleanup-empty-conversations': {
        'task': 'core.tasks.cleanup_empty_conversations',
        'schedule': 86400.0,  # Run every 24 hours
    },
}
```

## Testing the System

### 1. **Test Command**
```bash
python manage.py test_message_deletion
```

This command:
- Creates test users and conversations
- Creates messages with different timestamps
- Creates dummy media files
- Tests the deletion logic
- Verifies media file deletion

### 2. **Manual Deletion Command**
```bash
# Dry run (show what would be deleted)
python manage.py delete_expired_messages --dry-run

# Actually delete expired messages
python manage.py delete_expired_messages

# Delete messages older than custom hours
python manage.py delete_expired_messages --hours 48
```

### 3. **Testing with Real Data**
1. Send messages with images/videos
2. Wait for the deletion time to pass
3. Run the deletion task
4. Verify messages and files are removed

## File Structure
```
media/
├── chat_media/
│   ├── images/     # Image files (deleted after 24h)
│   └── videos/     # Video files (deleted after 24h)
└── profile_pics/   # Profile pictures (not auto-deleted)

core/
├── tasks.py        # Celery tasks for deletion
└── management/
    └── commands/
        ├── test_message_deletion.py      # Test command
        └── delete_expired_messages.py    # Manual deletion command

chat/
└── models.py       # Message model with deletion methods
```

## Security and Privacy

### 1. **Data Protection**
- Messages are permanently deleted, not just hidden
- Media files are physically removed from storage
- No recovery mechanism (ensures privacy)

### 2. **User Control**
- Users can configure their own deletion time
- Different users can have different deletion periods
- Respects individual privacy preferences

### 3. **Error Handling**
- Graceful handling of missing files
- Logging of deletion errors
- Continues deletion even if some files fail

## Monitoring and Logging

### 1. **Task Logging**
- Start/completion of deletion tasks
- Number of messages deleted
- Error counts and details
- Success confirmations

### 2. **File Deletion Logging**
- Confirmation of file deletions
- Error messages for failed deletions
- Path information for debugging

### 3. **Performance Monitoring**
- Task execution time
- Memory usage during deletion
- Database query performance

## Troubleshooting

### 1. **Messages Not Being Deleted**
- Check if Celery is running
- Verify task schedule in celery.py
- Check user's deletion_hours setting
- Review task logs for errors

### 2. **Media Files Not Deleted**
- Check file permissions on media directories
- Verify file paths are correct
- Check storage backend configuration
- Review deletion method logs

### 3. **Performance Issues**
- Consider batch processing for large datasets
- Optimize database queries
- Monitor disk I/O during deletion
- Adjust task frequency if needed

## Configuration Options

### 1. **User Profile Settings**
```python
# In accounts/models.py
message_deletion_hours = models.IntegerField(
    default=24, 
    help_text="Hours after which messages are deleted"
)
```

### 2. **Task Scheduling**
```python
# In kothakow/celery.py
'delete-expired-messages': {
    'task': 'core.tasks.delete_expired_messages',
    'schedule': 3600.0,  # Run every hour
}
```

### 3. **Storage Configuration**
```python
# In settings.py
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

## Best Practices

### 1. **Regular Testing**
- Test deletion logic regularly
- Verify media file cleanup
- Monitor task performance
- Check error logs

### 2. **Backup Considerations**
- Ensure important data is backed up before deletion
- Consider retention policies for compliance
- Document deletion procedures

### 3. **User Communication**
- Inform users about automatic deletion
- Provide clear settings for deletion time
- Explain privacy benefits

## Future Enhancements

### 1. **Advanced Features**
- Selective message retention
- Bulk deletion controls
- Deletion history tracking
- Recovery options (with admin approval)

### 2. **Performance Improvements**
- Database-level deletion queries
- Async file deletion
- Batch processing for large datasets
- Caching for deletion checks

### 3. **Monitoring Enhancements**
- Real-time deletion metrics
- User notification of deletions
- Admin dashboard for deletion stats
- Automated health checks 

## WebSocket Troubleshooting Note

For message deletion and real-time features to work locally, ensure you are running only one server (Daphne or Django 5+ runserver) on port 8000. Do not run both at the same time. 