# Media Upload Fix Implementation

## Problem Identified
The media files (images and videos) couldn't be sent in messages due to several issues in the frontend JavaScript logic and form structure.

## Issues Found and Fixed

### 1. **File Input Name Issue**
**Problem**: The file input had `name="image"` but the backend expected both `image` and `video` fields.
**Fix**: Changed the file input name to `name="file"` and updated JavaScript to dynamically assign the correct field name based on file type.

### 2. **JavaScript Form Submission Logic Error**
**Problem**: The form submission logic was flawed - it only sent files via AJAX if there was no content, but the logic was incorrect.
**Fix**: Completely rewrote the form submission logic to:
- Check if there's a file to upload first
- Send files via AJAX with proper field names
- Send text-only messages via WebSocket
- Handle both scenarios correctly

### 3. **Missing File Type Validation**
**Problem**: No validation for file types and sizes.
**Fix**: Added comprehensive validation:
- File type checking (image/* or video/*)
- File size validation (max 10MB)
- Visual feedback for invalid files

### 4. **Poor User Experience**
**Problem**: No loading states or visual feedback during upload.
**Fix**: Added:
- Loading spinner during upload
- File type icons (image/video)
- File size display
- Visual feedback for selected files
- Better error handling and user feedback

## Technical Changes Made

### Frontend Changes (`templates/chat/conversation_detail.html`)

#### 1. Form Structure
```html
<!-- Before -->
<input type="file" id="file-input" name="image" accept="image/*,video/*">

<!-- After -->
<input type="file" id="file-input" name="file" accept="image/*,video/*">
```

#### 2. JavaScript Form Submission Logic
```javascript
// New logic that properly handles both text and media messages
if (fileInput && fileInput.files.length > 0) {
    // Handle file upload via AJAX
    const file = fileInput.files[0];
    const isImage = file.type.startsWith('image/');
    const isVideo = file.type.startsWith('video/');
    
    // Create proper FormData with correct field names
    if (isImage) {
        uploadFormData.append('image', file);
    } else if (isVideo) {
        uploadFormData.append('video', file);
    }
} else {
    // Handle text-only messages via WebSocket
}
```

#### 3. Enhanced User Experience
- **File Type Validation**: Checks if file is image or video
- **File Size Validation**: Maximum 10MB limit
- **Visual Feedback**: Different icons for images vs videos
- **Loading States**: Spinner during upload
- **Error Handling**: Clear error messages

#### 4. CSS Improvements
```css
.file-upload-area.has-file {
    border-color: #28a745;
    background-color: #d4edda;
}
```

### Backend Changes (`chat/views.py`)

#### 1. Debug Logging Added
```python
# Debug logging to help identify issues
print(f"DEBUG: conversation_id={conversation_id}")
print(f"DEBUG: content={content}")
print(f"DEBUG: image={image}")
print(f"DEBUG: video={video}")
print(f"DEBUG: FILES keys={list(request.FILES.keys())}")
```

#### 2. Directory Structure
Created necessary directories for media storage:
- `media/chat_media/images/` - for image files
- `media/chat_media/videos/` - for video files

## How to Test the Media Upload

### 1. **Start the Development Server**
```bash
python manage.py runserver
```

### 2. **Test Image Upload**
1. Navigate to a conversation
2. Click the paperclip icon to open file upload area
3. Select an image file (JPG, PNG, GIF, etc.)
4. Add optional text message
5. Click send
6. Verify the image appears in the chat

### 3. **Test Video Upload**
1. Follow the same steps as image upload
2. Select a video file (MP4, AVI, etc.)
3. Verify the video appears with controls

### 4. **Test File Validation**
1. Try uploading a non-image/video file (should show error)
2. Try uploading a file larger than 10MB (should show error)
3. Verify proper error messages are displayed

### 5. **Test Drag and Drop**
1. Drag an image or video file onto the upload area
2. Verify the file is selected and shows proper info
3. Send the message and verify it appears

## File Structure
```
media/
├── chat_media/
│   ├── images/     # Uploaded image files
│   └── videos/     # Uploaded video files
├── profile_pics/   # User profile pictures
└── ...

templates/chat/
└── conversation_detail.html  # Updated with fix

chat/
├── views.py        # Added debug logging
└── models.py       # No changes needed

test_upload.html    # Test file for verification
```

## Browser Console Debugging

When testing, check the browser console for:
- `Response status: 200` - indicates successful request
- `Response data: {...}` - shows the server response
- Any error messages for debugging

## Common Issues and Solutions

### 1. **File Not Uploading**
- Check browser console for errors
- Verify file size is under 10MB
- Ensure file type is image or video
- Check network tab for failed requests

### 2. **File Uploads but Doesn't Display**
- Check if media directories exist
- Verify Django media settings
- Check file permissions on media directories

### 3. **WebSocket Issues**
- Media files are sent via AJAX, not WebSocket
- Text messages use WebSocket for real-time delivery
- Check if WebSocket connection is established

## Security Considerations

1. **File Type Validation**: Only allows image and video files
2. **File Size Limits**: Maximum 10MB per file
3. **CSRF Protection**: All uploads include CSRF tokens
4. **User Authentication**: Only authenticated users can upload
5. **Conversation Access**: Users can only upload to conversations they're part of

## Performance Optimizations

1. **File Size Limits**: Prevents large file uploads
2. **Client-side Validation**: Reduces server load
3. **Loading States**: Provides user feedback
4. **Error Handling**: Prevents failed uploads from blocking UI

## Future Enhancements

1. **Image Compression**: Automatically compress large images
2. **Video Thumbnails**: Generate thumbnails for video files
3. **Progress Bars**: Show upload progress for large files
4. **Multiple File Upload**: Allow selecting multiple files at once
5. **File Preview**: Show preview before sending

## Testing Checklist

- [ ] Image upload works
- [ ] Video upload works
- [ ] File type validation works
- [ ] File size validation works
- [ ] Drag and drop works
- [ ] Error messages are clear
- [ ] Loading states work
- [ ] Files display correctly in chat
- [ ] WebSocket still works for text messages
- [ ] No console errors 

## Troubleshooting 404 Errors for Media/Static Files

If you see 404 errors for media or static files (e.g., profile pictures, notification sounds):

1. Check that the files exist in the correct directories:
   - `media/profile_pics/`
   - `media/chat_media/images/`
   - `media/chat_media/videos/`
   - `static/audios/`
2. If a file is missing, either add it or update your code/templates to not reference it.
3. For notification sounds, ensure `static/audios/web_notification.mp3` exists or update the JS to use a different sound.
4. Restart your development server after adding new files. 