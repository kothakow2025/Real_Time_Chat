from django.contrib import admin
from .models import Conversation, Message, MessageReadStatus
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('timestamp',)
    fields = ('sender', 'message_type', 'content', 'image', 'video', 'timestamp')
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_participants', 'get_message_count', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('participants__username',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MessageInline]
    
    def get_participants(self, obj):
        return ", ".join([user.username for user in obj.participants.all()])
    get_participants.short_description = 'Participants'
    
    def get_message_count(self, obj):
        return obj.messages.count()
    get_message_count.short_description = 'Messages'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_conversation_participants', 'sender', 'message_type', 'get_content_preview', 'timestamp')
    list_filter = ('message_type', 'timestamp')
    search_fields = ('sender__username', 'content', 'conversation__participants__username')
    readonly_fields = ('timestamp',)
    
    fieldsets = (
        ('Message Info', {
            'fields': ('conversation', 'sender', 'message_type')
        }),
        ('Content', {
            'fields': ('content', 'image', 'video')
        }),
        ('Metadata', {
            'fields': ('timestamp',)
        }),
    )
    
    def get_conversation_participants(self, obj):
        participants = obj.conversation.participants.all()
        return ", ".join([user.username for user in participants])
    get_conversation_participants.short_description = 'Conversation'
    
    def get_content_preview(self, obj):
        if obj.message_type == 'text':
            return obj.content[:50] + '...' if obj.content and len(obj.content) > 50 else obj.content or '-'
        elif obj.message_type == 'image' and obj.image:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 100px; max-height: 100px;"/></a>',
                obj.image.url, obj.image.url
            )
        elif obj.message_type == 'video' and obj.video:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.video.url, obj.video.name.split('/')[-1]
            )
        return '-'
    get_content_preview.short_description = 'Content'
    get_content_preview.allow_tags = True
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender', 'conversation')

@admin.register(MessageReadStatus)
class MessageReadStatusAdmin(admin.ModelAdmin):
    list_display = ('message', 'user', 'is_read')
    list_filter = ('is_read',)
    search_fields = ('message__content', 'user__username')
    readonly_fields = ()
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('message', 'user')

# Custom admin site configuration
admin.site.site_header = "Kotha Kow Admin"
admin.site.site_title = "Kotha Kow Admin Portal"
admin.site.index_title = "Welcome to Kotha Kow Administration"
