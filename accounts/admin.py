from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, FriendRequest

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('profile_picture', 'is_online', 'last_seen', 'message_deletion_hours')
    readonly_fields = ('is_online', 'last_seen')

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'get_is_online', 'get_last_seen')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'userprofile__is_online')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    def get_is_online(self, obj):
        try:
            return obj.userprofile.is_online
        except UserProfile.DoesNotExist:
            return False
    get_is_online.boolean = True
    get_is_online.short_description = 'Online'
    
    def get_last_seen(self, obj):
        try:
            return obj.userprofile.last_seen
        except UserProfile.DoesNotExist:
            return None
    get_last_seen.short_description = 'Last Seen'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_online', 'last_seen', 'message_deletion_hours')
    list_filter = ('is_online', 'message_deletion_hours')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('is_online', 'last_seen')
    
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'profile_picture')
        }),
        ('Status', {
            'fields': ('is_online', 'last_seen')
        }),
        ('Settings', {
            'fields': ('message_deletion_hours',)
        }),
    )

@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('from_user__username', 'to_user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Request Info', {
            'fields': ('from_user', 'to_user', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
