from accounts.models import FriendRequest
from chat.models import MessageReadStatus, Conversation
from django.db.models import Q

def navbar_counts(request):
    friend_request_count = 0
    unread_message_count = 0
    if request.user.is_authenticated:
        # Pending friend requests sent TO the user
        friend_request_count = FriendRequest.objects.filter(to_user=request.user, status='pending').count()
        # Unread messages in conversations
        unread_message_count = MessageReadStatus.objects.filter(user=request.user, is_read=False).count()
    return {
        'navbar_friend_request_count': friend_request_count,
        'navbar_unread_message_count': unread_message_count,
    } 