from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Max
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Conversation, Message, MessageReadStatus
from accounts.models import FriendRequest
import json

@login_required
def dashboard(request):
    # Get conversations where user is a participant
    conversations = Conversation.objects.filter(
        participants=request.user
    ).annotate(
        last_message_time=Max('messages__timestamp')
    ).order_by('-last_message_time')
    
    # Get unread message counts for each conversation
    conversation_data = []
    for conv in conversations:
        unread_count = Message.objects.filter(
            conversation=conv
        ).exclude(
            messagereadstatus__user=request.user,
            messagereadstatus__is_read=True
        ).count()
        
        # Get the other participant
        other_participant = conv.participants.exclude(id=request.user.id).first()
        
        # Get last message
        last_message = conv.messages.order_by('-timestamp').first()
        
        conversation_data.append({
            'conversation': conv,
            'other_participant': other_participant,
            'unread_count': unread_count,
            'last_message': last_message
        })
    
    context = {
        'conversation_data': conversation_data
    }
    
    return render(request, 'chat/dashboard.html', context)

@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(
        Conversation, 
        id=conversation_id, 
        participants=request.user
    )
    
    # Get the other participant
    other_participant = conversation.participants.exclude(id=request.user.id).first()
    
    # Get messages with pagination
    messages = conversation.messages.select_related(
        'sender__userprofile'
    ).order_by('-timestamp')
    
    # Filter out unsent messages for other users
    messages = messages.filter(
        Q(is_unsent=False) | Q(sender=request.user)
    )
    
    paginator = Paginator(messages, 50)  # Show 50 messages per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Mark messages as read
    unread_messages = Message.objects.filter(
        conversation=conversation
    ).exclude(
        messagereadstatus__user=request.user,
        messagereadstatus__is_read=True
    )
    
    for message in unread_messages:
        MessageReadStatus.objects.update_or_create(
            message=message,
            user=request.user,
            defaults={'is_read': True}
        )
    
    context = {
        'conversation': conversation,
        'other_participant': other_participant,
        'messages': page_obj,
        'page_obj': page_obj
    }
    
    return render(request, 'chat/conversation_detail.html', context)

@login_required
@require_POST
def send_message(request):
    conversation_id = request.POST.get('conversation_id')
    content = request.POST.get('content', '').strip()
    image = request.FILES.get('image')
    video = request.FILES.get('video')
    
    # Debug logging
    print(f"DEBUG: conversation_id={conversation_id}")
    print(f"DEBUG: content={content}")
    print(f"DEBUG: image={image}")
    print(f"DEBUG: video={video}")
    print(f"DEBUG: FILES keys={list(request.FILES.keys())}")
    print(f"DEBUG: POST keys={list(request.POST.keys())}")
    
    if not conversation_id:
        return JsonResponse({'success': False, 'message': 'Conversation ID required'})
    
    conversation = get_object_or_404(
        Conversation, 
        id=conversation_id, 
        participants=request.user
    )
    
    # Validate that there's content or media
    if not content and not image and not video:
        return JsonResponse({'success': False, 'message': 'Message content or media required'})
    
    # Validate file type and size
    max_size = 10 * 1024 * 1024  # 10MB
    if image:
        print(f"DEBUG: Processing image - type: {image.content_type}, size: {image.size}")
        if not image.content_type.startswith('image/'):
            return JsonResponse({'success': False, 'message': 'Only image files are allowed for images.'})
        if image.size > max_size:
            return JsonResponse({'success': False, 'message': 'media size is too large, please use 10MB or below size files'})
    if video:
        print(f"DEBUG: Processing video - type: {video.content_type}, size: {video.size}")
        if not video.content_type.startswith('video/'):
            return JsonResponse({'success': False, 'message': 'Only video files are allowed for videos.'})
        if video.size > max_size:
            return JsonResponse({'success': False, 'message': 'media size is too large, please use 10MB or below size files'})
    
    # Determine message type
    if image:
        message_type = 'image'
    elif video:
        message_type = 'video'
    else:
        message_type = 'text'

    print(f"DEBUG: Creating message with type: {message_type}")
    
    # Create message
    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content,
        image=image,
        video=video,
        message_type=message_type
    )
    
    print(f"DEBUG: Message created with ID: {message.id}")
    
    # Mark as read for sender
    MessageReadStatus.objects.create(
        message=message,
        user=request.user,
        is_read=True
    )
    
    # Broadcast the message via WebSocket
    try:
        channel_layer = get_channel_layer()
        
        sender_profile_pic_url = request.user.userprofile.profile_picture.url if request.user.userprofile.profile_picture else None
        image_url = message.image.url if message.image else None
        video_url = message.video.url if message.video else None

        async_to_sync(channel_layer.group_send)(
            f'chat_{conversation.id}',
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'sender_id': request.user.id,
                    'sender_username': request.user.username,
                    'sender_profile_picture_url': sender_profile_pic_url,
                    'content': message.content,
                    'timestamp': message.timestamp.isoformat(),
                    'image_url': image_url,
                    'video_url': video_url,
                    'is_edited': message.is_edited,
                    'is_unsent': message.is_unsent,
                    'edited_at': message.edited_at.isoformat() if message.edited_at else None,
                }
            }
        )
    except Exception as e:
        # Log error but don't prevent the HTTP response
        print(f"Error sending message via WebSocket: {e}")

    response_data = {
        'success': True,
        'message_id': message.id,
        'timestamp': message.timestamp.isoformat(),
        'image_url': message.image.url if message.image else None,
        'video_url': message.video.url if message.video else None
    }
    
    print(f"DEBUG: Returning response: {response_data}")
    return JsonResponse(response_data)

@login_required
def get_messages(request, conversation_id):
    """API endpoint to get messages for a conversation (for AJAX updates)"""
    conversation = get_object_or_404(
        Conversation, 
        id=conversation_id, 
        participants=request.user
    )
    
    # Get messages after a certain timestamp if provided
    after_timestamp = request.GET.get('after')
    messages_query = conversation.messages.select_related(
        'sender__userprofile'
    ).order_by('timestamp')
    
    if after_timestamp:
        from django.utils.dateparse import parse_datetime
        after_dt = parse_datetime(after_timestamp)
        if after_dt:
            messages_query = messages_query.filter(timestamp__gt=after_dt)
    
    messages = messages_query[:50]  # Limit to 50 messages
    
    messages_data = []
    for message in messages:
        # Check if message is read by current user
        is_read = MessageReadStatus.objects.filter(
            message=message,
            user=request.user,
            is_read=True
        ).exists()
        
        message_data = {
            'id': message.id,
            'content': message.content,
            'sender_id': message.sender.id,
            'sender_username': message.sender.username,
            'sender_profile_picture': message.sender.userprofile.profile_picture.url if message.sender.userprofile.profile_picture else None,
            'timestamp': message.timestamp.isoformat(),
            'is_read': is_read,
            'image_url': message.image.url if message.image else None,
            'video_url': message.video.url if message.video else None
        }
        messages_data.append(message_data)
    
    return JsonResponse({'messages': messages_data})

@login_required
@require_POST
def mark_messages_read(request):
    """Mark messages as read"""
    conversation_id = request.POST.get('conversation_id')
    
    if not conversation_id:
        return JsonResponse({'success': False, 'message': 'Conversation ID required'})
    
    conversation = get_object_or_404(
        Conversation, 
        id=conversation_id, 
        participants=request.user
    )
    
    # Mark all unread messages in this conversation as read
    unread_messages = Message.objects.filter(
        conversation=conversation
    ).exclude(
        messagereadstatus__user=request.user,
        messagereadstatus__is_read=True
    )
    
    for message in unread_messages:
        MessageReadStatus.objects.update_or_create(
            message=message,
            user=request.user,
            defaults={'is_read': True}
        )
    
    return JsonResponse({'success': True})

@login_required
def start_conversation(request, user_id):
    """Start a new conversation with a user (if they are friends)"""
    other_user = get_object_or_404(User, id=user_id)
    
    # Check if users are friends (have accepted friend request)
    friendship = FriendRequest.objects.filter(
        Q(from_user=request.user, to_user=other_user, status='accepted') |
        Q(from_user=other_user, to_user=request.user, status='accepted')
    ).first()
    
    if not friendship:
        return redirect('accounts:user_list')
    
    # Check if conversation already exists
    existing_conversation = Conversation.objects.filter(
        participants=request.user
    ).filter(
        participants=other_user
    ).first()
    
    if existing_conversation:
        return redirect('chat:conversation_detail', conversation_id=existing_conversation.id)
    
    # Create new conversation
    conversation = Conversation.objects.create()
    conversation.participants.add(request.user, other_user)
    
    return redirect('chat:conversation_detail', conversation_id=conversation.id)

@login_required
@require_POST
def edit_message(request):
    """Edit a message"""
    message_id = request.POST.get('message_id')
    new_content = request.POST.get('content', '').strip()
    
    if not message_id or not new_content:
        return JsonResponse({'success': False, 'message': 'Message ID and content are required'})
    
    try:
        message = Message.objects.get(id=message_id)
        
        # Check if user can edit this message
        if not message.can_be_edited(request.user):
            return JsonResponse({'success': False, 'message': 'You cannot edit this message'})
        
        # Edit the message
        message.edit_message(new_content)
        
        # Broadcast the edit via WebSocket
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'chat_{message.conversation.id}',
                {
                    'type': 'message_edited',
                    'message': {
                        'id': message.id,
                        'content': message.content,
                        'is_edited': message.is_edited,
                        'edited_at': message.edited_at.isoformat() if message.edited_at else None,
                    }
                }
            )
        except Exception as e:
            print(f"Error sending edit via WebSocket: {e}")
        
        return JsonResponse({
            'success': True,
            'message': 'Message edited successfully',
            'content': message.content,
            'is_edited': message.is_edited,
            'edited_at': message.edited_at.isoformat() if message.edited_at else None,
        })
        
    except Message.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Message not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error editing message: {str(e)}'})

@login_required
@require_POST
def unsend_message(request):
    """Unsend a message"""
    message_id = request.POST.get('message_id')
    
    if not message_id:
        return JsonResponse({'success': False, 'message': 'Message ID is required'})
    
    try:
        message = Message.objects.get(id=message_id)
        
        # Check if user can unsend this message
        if not message.can_be_unsent(request.user):
            return JsonResponse({'success': False, 'message': 'You cannot unsend this message'})
        
        # Unsend the message
        message.unsend_message()
        
        # Broadcast the unsend via WebSocket
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'chat_{message.conversation.id}',
                {
                    'type': 'message_unsent',
                    'message': {
                        'id': message.id,
                        'is_unsent': message.is_unsent,
                    }
                }
            )
        except Exception as e:
            print(f"Error sending unsend via WebSocket: {e}")
        
        return JsonResponse({
            'success': True,
            'message': 'Message unsent successfully',
            'is_unsent': message.is_unsent,
        })
        
    except Message.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Message not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error unsending message: {str(e)}'})
