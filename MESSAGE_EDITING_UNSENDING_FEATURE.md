# Message Editing and Unsending Feature

This document describes the implementation of message editing and unsending functionality in the Real-Time Chat Application, similar to popular messaging apps like Messenger.

## Features Implemented

### 1. Message Editing
- **Time Limit**: Users can edit their text messages within 15 minutes of sending
- **Restrictions**: 
  - Only the sender can edit their own messages
  - Only text messages can be edited (not images or videos)
  - Unsent messages cannot be edited
- **Visual Indicators**: Edited messages show "(edited)" next to the timestamp
- **Real-time Updates**: Changes are broadcast to all participants in real-time via WebSocket

### 2. Message Unsending
- **Time Limit**: Users can unsend their messages within 1 hour of sending
- **Restrictions**:
  - Only the sender can unsend their own messages
  - Already unsent messages cannot be unsent again
- **Visual Behavior**: 
  - Unsent messages show "This message was unsent" instead of the original content
  - Message appears faded/opacity reduced
  - Edit and unsend buttons are disabled for unsent messages
- **Privacy**: Unsent messages are hidden from other users (they see the unsent indicator)

## Technical Implementation

### Database Changes
Added new fields to the `Message` model:
- `is_edited`: Boolean field indicating if the message has been edited
- `is_unsent`: Boolean field indicating if the message has been unsent
- `edited_at`: DateTime field recording when the message was last edited

### Backend Changes

#### Models (`chat/models.py`)
- Added `can_be_edited(user)` method to check editing permissions
- Added `can_be_unsent(user)` method to check unsending permissions
- Added `edit_message(new_content)` method to edit message content
- Added `unsend_message()` method to mark message as unsent

#### Views (`chat/views.py`)
- Added `edit_message()` view to handle message editing via AJAX
- Added `unsend_message()` view to handle message unsending via AJAX
- Updated message broadcasting to include new fields
- Added filtering to hide unsent messages from other users

#### WebSocket Consumer (`chat/consumers.py`)
- Added handlers for `edit_message` and `unsend_message` WebSocket events
- Added `message_edited` and `message_unsent` broadcast handlers
- Updated message payload to include editing/unsending status

#### URLs (`chat/urls.py`)
- Added `/edit-message/` endpoint for message editing
- Added `/unsend-message/` endpoint for message unsending

### Frontend Changes

#### Template (`templates/chat/conversation_detail.html`)
- Added message action buttons (edit/unsend) that appear on hover
- Added edit forms with save/cancel buttons
- Added visual indicators for edited and unsent messages
- Updated message styling for unsent messages

#### JavaScript
- Added `showEditForm()`, `saveEdit()`, `cancelEdit()` functions for editing
- Added `unsendMessage()` function for unsending
- Added `updateMessageContent()` and `markMessageAsUnsent()` for real-time updates
- Updated `addMessageToChat()` to include edit/unsend functionality
- Added WebSocket handlers for edit/unsend events

## Usage

### Editing a Message
1. Hover over your own text message
2. Click the edit button (pencil icon)
3. Modify the text in the input field
4. Click "Save" to confirm or "Cancel" to discard changes

### Unsending a Message
1. Hover over your own message
2. Click the unsend button (trash icon)
3. Confirm the action in the popup dialog

## Security and Privacy

- **Authorization**: Only message senders can edit or unsend their messages
- **Time Limits**: Prevents abuse by limiting when actions can be performed
- **Content Filtering**: Unsent messages are hidden from other users
- **CSRF Protection**: All AJAX requests include CSRF tokens
- **Input Validation**: Server-side validation of all edit/unsend requests

## Limitations

1. **Text Only**: Only text messages can be edited (not media)
2. **Time Restrictions**: 
   - Edit: 15 minutes from sending
   - Unsend: 1 hour from sending
3. **No History**: No record of previous edits is maintained
4. **No Bulk Operations**: Each message must be edited/unsent individually

## Future Enhancements

Potential improvements that could be added:
- Edit history tracking
- Bulk message operations
- Media message editing (replace images/videos)
- Extended time limits for premium users
- Message reactions and replies
- Message forwarding with edit/unsend status

## Testing

The functionality has been tested with:
- Unit tests for model methods
- Integration tests for views and WebSocket handlers
- Manual testing of the complete user flow
- Cross-browser compatibility testing

## Migration

To apply the database changes:
```bash
python manage.py makemigrations chat
python manage.py migrate
```

The new fields are added with default values, so existing messages will work without modification. 