from django.core.management.base import BaseCommand
from django.utils import timezone
from chat.models import Message
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Manually delete expired messages and their media files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Delete messages older than this many hours (default: 24)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hours = options['hours']
        
        self.stdout.write(f'{"[DRY RUN] " if dry_run else ""}Deleting messages older than {hours} hours...')
        
        # Get all messages that should be deleted
        messages_to_delete = []
        
        # Get messages with their sender profiles to check deletion settings
        messages = Message.objects.select_related('sender__userprofile').all()
        
        for message in messages:
            if message.should_be_deleted():
                messages_to_delete.append(message)
        
        self.stdout.write(f'Found {len(messages_to_delete)} messages to delete')
        
        if not messages_to_delete:
            self.stdout.write(self.style.SUCCESS('No messages to delete'))
            return
        
        # Show what would be deleted
        self.stdout.write('\nMessages to be deleted:')
        for message in messages_to_delete:
            media_info = []
            if message.image:
                media_info.append('image')
            if message.video:
                media_info.append('video')
            
            media_str = f" (with {', '.join(media_info)})" if media_info else ""
            
            self.stdout.write(
                f'  - Message {message.id}: "{message.content[:50]}..." by {message.sender.username} '
                f'({message.timestamp}){media_str}'
            )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN: No messages were actually deleted'))
            return
        
        # Confirm deletion
        confirm = input('\nAre you sure you want to delete these messages? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write('Deletion cancelled')
            return
        
        # Delete messages with their media files
        deleted_count = 0
        error_count = 0
        
        for message in messages_to_delete:
            try:
                self.stdout.write(f'Deleting message {message.id}...')
                message.delete_with_media()
                deleted_count += 1
                self.stdout.write(self.style.SUCCESS(f'Successfully deleted message {message.id}'))
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'Error deleting message {message.id}: {str(e)}'))
        
        self.stdout.write(f'\nDeletion completed: {deleted_count} messages deleted, {error_count} errors')
        
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f'There were {error_count} errors during deletion'))
        else:
            self.stdout.write(self.style.SUCCESS('All messages deleted successfully')) 