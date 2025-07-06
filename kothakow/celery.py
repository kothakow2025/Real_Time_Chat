import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kothakow.settings')

app = Celery('kothakow')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule
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

app.conf.timezone = 'Asia/Dhaka'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')