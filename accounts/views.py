from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from typing import Optional, Dict, Any

from .forms import SignUpForm, UserUpdateForm, ProfileUpdateForm
from .models import UserProfile, FriendRequest
from chat.models import Conversation

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('chat:dashboard')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})

@login_required
def profile_settings(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.userprofile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('accounts:profile_settings')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.userprofile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'accounts/profile_settings.html', context)

@login_required
def user_list(request):
    # Get all users except current user
    users = User.objects.exclude(id=request.user.id).select_related('userprofile')
    
    # Get friend requests status
    sent_requests = FriendRequest.objects.filter(
        from_user=request.user
    ).values_list('to_user_id', 'status')
    
    received_requests = FriendRequest.objects.filter(
        to_user=request.user
    ).values_list('from_user_id', 'status')
    
    # Create dictionaries for easy lookup
    sent_status = {user_id: status for user_id, status in sent_requests}
    received_status = {user_id: status for user_id, status in received_requests}
    
    # Exclude users with pending or accepted requests (sent or received)
    exclude_ids = set()
    for user_id, status in sent_requests:
        if status in ['pending', 'accepted']:
            exclude_ids.add(user_id)
    for user_id, status in received_requests:
        if status in ['pending', 'accepted']:
            exclude_ids.add(user_id)
    
    filtered_users = [user for user in users if user.id not in exclude_ids]
    
    # Add status to each user
    user_data = []
    for user in filtered_users:
        status = 'none'
        if user.id in sent_status:
            status = f'sent_{sent_status[user.id]}'
        elif user.id in received_status:
            status = f'received_{received_status[user.id]}'
        user_data.append({
            'user': user,
            'status': status
        })
    
    return render(request, 'accounts/user_list.html', {'user_data': user_data})

@login_required
@require_POST
def send_friend_request(request):
    to_user_id = request.POST.get('to_user')
    
    if not to_user_id or not to_user_id.isdigit():
        return JsonResponse({'success': False, 'message': 'Invalid user ID provided.'}, status=400)

    to_user = get_object_or_404(User, id=to_user_id)

    if to_user == request.user:
        return JsonResponse({'success': False, 'message': 'You cannot send a friend request to yourself.'})

    # Check for existing request (pending or accepted)
    existing_request = FriendRequest.objects.filter(
        (Q(from_user=request.user, to_user=to_user) | Q(from_user=to_user, to_user=request.user))
    ).first()

    if existing_request:
        if existing_request.status == 'accepted':
            return JsonResponse({'success': False, 'message': 'You are already friends.'})
        else:
            return JsonResponse({'success': False, 'message': 'A friend request already exists.'})

    # Create the friend request
    FriendRequest.objects.create(from_user=request.user, to_user=to_user, status='pending')
    
    # Send notification via WebSocket
    try:
        channel_layer = get_channel_layer()
        notification_message = f"{(request.user.get_full_name() or request.user.username)} sent you a friend request."
        
        async_to_sync(channel_layer.group_send)(
            f'notifications_{to_user.id}',
            {
                'type': 'send_notification',
                'notification': {
                    'type': 'friend_request',
                    'message': notification_message,
                    'from_user': {
                        'id': request.user.id,
                        'username': request.user.username,
                        'full_name': request.user.get_full_name() or ''
                    }
                }
            }
        )
    except Exception as e:
        # Log error but don't block the request if notification fails
        print(f"Error sending notification: {e}")

    return JsonResponse({'success': True, 'message': 'Friend request sent successfully.'})

@login_required
@require_POST
def respond_friend_request(request):
    request_id = request.POST.get('request_id')
    action = request.POST.get('action')  # 'accept' or 'reject'

    friend_request = get_object_or_404(
        FriendRequest,
        id=request_id,
        to_user=request.user,
        status='pending'
    )

    from_user_id = friend_request.from_user.id

    if action == 'accept':
        friend_request.status = 'accepted'
        friend_request.save()

        # Create conversation between users
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, friend_request.from_user)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': "You're added"})
        else:
            return redirect('accounts:friend_requests')
        
    elif action == 'reject':
        friend_request.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': "Friend request rejected"})
        else:
            return redirect('accounts:friend_requests')
    
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)
        else:
            return redirect('accounts:friend_requests')

@login_required
def friend_requests(request):
    # Get pending friend requests received by current user
    received_requests = FriendRequest.objects.filter(
        to_user=request.user,
        status='pending'
    ).select_related('from_user__userprofile')
    
    # Get sent requests
    sent_requests = FriendRequest.objects.filter(
        from_user=request.user
    ).select_related('to_user__userprofile')
    
    # Get accepted friends
    accepted_friends = FriendRequest.objects.filter(
        (Q(from_user=request.user) | Q(to_user=request.user)) & 
        Q(status='accepted')
    ).select_related('from_user__userprofile', 'to_user__userprofile')
    
    # Process friends to get the other user (not the current user)
    friends_list = []
    for friend_request in accepted_friends:
        if friend_request.from_user == request.user:
            friends_list.append({
                'user': friend_request.to_user,
                'friend_request': friend_request
            })
        else:
            friends_list.append({
                'user': friend_request.from_user,
                'friend_request': friend_request
            })
    
    context = {
        'received_requests': received_requests,
        'sent_requests': sent_requests,
        'friends_list': friends_list
    }
    
    return render(request, 'accounts/friend_requests.html', context)

@login_required
def user_profile(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    # Check friendship status
    friendship_status = 'none'
    friend_request = FriendRequest.objects.filter(
        Q(from_user=request.user, to_user=user) |
        Q(from_user=user, to_user=request.user)
    ).first()
    
    if friend_request:
        if friend_request.from_user == request.user:
            friendship_status = f'sent_{friend_request.status}'
        else:
            friendship_status = f'received_{friend_request.status}'
    
    context = {
        'profile_user': user,
        'friendship_status': friendship_status,
        'friend_request': friend_request
    }
    
    return render(request, 'accounts/user_profile.html', context)

@login_required
@require_POST
def delete_account(request):
    """Delete user account and all associated data"""
    user = request.user
    
    # Log out the user
    logout(request)
    
    # Delete the user (this will cascade delete related objects)
    user.delete()
    
    # Add a success message
    messages.success(request, 'Your account has been successfully deleted.')
    
    # Redirect to home page
    return redirect('accounts:login')

@login_required
@require_POST
def unfriend_user(request):
    friend_id = request.POST.get('user_id')
    if not friend_id or not friend_id.isdigit():
        return JsonResponse({'success': False, 'message': 'Invalid user ID.'}, status=400)
    
    friend = get_object_or_404(User, id=friend_id)
    
    # Check if they are actually friends
    friend_request = FriendRequest.objects.filter(
        (Q(from_user=request.user, to_user=friend) | Q(from_user=friend, to_user=request.user)) & 
        Q(status='accepted')
    ).first()
    
    if not friend_request:
        return JsonResponse({'success': False, 'message': 'You are not friends with this user.'}, status=400)
    
    try:
        # Import here to avoid circular imports
        from chat.models import Conversation, Message
        import os
        
        # Get conversations between the two users
        conversations = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=friend
        )
        
        # Delete all messages and their media files before deleting conversations
        for conversation in conversations:
            messages = conversation.messages.all()
            for message in messages:
                # Delete media files if they exist
                if message.image and os.path.exists(message.image.path):
                    try:
                        os.remove(message.image.path)
                    except OSError:
                        pass  # File might already be deleted
                
                if message.video and os.path.exists(message.video.path):
                    try:
                        os.remove(message.video.path)
                    except OSError:
                        pass  # File might already be deleted
                
                # Delete the message (this will also delete MessageReadStatus due to CASCADE)
                message.delete()
            
            # Delete the conversation
            conversation.delete()
        
        # Delete the friend request
        friend_request.delete()
        
        return JsonResponse({'success': True, 'message': 'Unfriended successfully. All conversations and media files have been permanently deleted.'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'An error occurred while unfriending: {str(e)}'}, status=500)

@login_required
@require_POST
def cancel_friend_request(request):
    to_user_id = request.POST.get('to_user')
    if not to_user_id or not to_user_id.isdigit():
        return JsonResponse({'success': False, 'message': 'Invalid user ID provided.'}, status=400)
    to_user = get_object_or_404(User, id=to_user_id)
    friend_request = FriendRequest.objects.filter(from_user=request.user, to_user=to_user, status='pending').first()
    if not friend_request:
        return JsonResponse({'success': False, 'message': 'No pending friend request found.'}, status=404)
    friend_request.delete()
    return JsonResponse({'success': True, 'message': 'Friend request cancelled.'})
