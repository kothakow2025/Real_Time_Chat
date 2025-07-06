from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Main chat URLs
    path('', views.dashboard, name='dashboard'),
    path('conversation/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('start-conversation/<int:user_id>/', views.start_conversation, name='start_conversation'),
    
    # AJAX/API URLs
    path('send-message/', views.send_message, name='send_message'),
    path('edit-message/', views.edit_message, name='edit_message'),
    path('unsend-message/', views.unsend_message, name='unsend_message'),
    path('api/messages/<int:conversation_id>/', views.get_messages, name='get_messages'),
    path('mark-messages-read/', views.mark_messages_read, name='mark_messages_read'),
]