from celery import shared_task
from django.utils import timezone
from chat.models import Message
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task
def delete_expired_messages():
    """
    Delete messages that have exceeded their deletion time based on user settings
    """
    logger.info("Starting expired message deletion task")
    deleted_count = 0
    error_count = 0
    
    # Get all messages that should be deleted
    messages_to_delete = []
    
    # More efficient query to get messages that should be deleted
    current_time = timezone.now()
    
    # Get messages with their sender profiles to check deletion settings
    messages = Message.objects.select_related('sender__userprofile').all()
    
    for message in messages:
        if message.should_be_deleted():
            messages_to_delete.append(message)
    
    logger.info(f"Found {len(messages_to_delete)} messages to delete")
    
    # Delete messages with their media files
    for message in messages_to_delete:
        try:
            message.delete_with_media()
            deleted_count += 1
            logger.info(f"Successfully deleted message {message.id} with media files")
        except Exception as e:
            error_count += 1
            logger.error(f"Error deleting message {message.id}: {str(e)}")
    
    logger.info(f"Task completed: {deleted_count} messages deleted, {error_count} errors")
    return f"Deleted {deleted_count} expired messages, {error_count} errors"

@shared_task
def cleanup_empty_conversations():
    """
    Remove conversations that have no messages
    """
    from chat.models import Conversation
    
    empty_conversations = Conversation.objects.filter(messages__isnull=True)
    count = empty_conversations.count()
    empty_conversations.delete()
    
    logger.info(f"Deleted {count} empty conversations")
    return f"Deleted {count} empty conversations"