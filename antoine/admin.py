from django.contrib import admin
from django.utils.html import format_html
from .models import UserProfile, LoginHistory, PasswordChangeHistory


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile model"""
    list_display = ('get_username', 'is_email_verified', 'created_at', 'last_login_ip')
    list_filter = ('is_email_verified', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'last_login_ip')
    readonly_fields = ('created_at', 'updated_at', 'last_login_ip')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'is_email_verified')
        }),
        ('Profile Details', {
            'fields': ('bio', 'avatar', 'phone_number')
        }),
        ('Security', {
            'fields': ('last_login_ip',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    """Admin interface for LoginHistory model"""
    list_display = ('get_username', 'ip_address', 'get_status_badge', 'login_time')
    list_filter = ('success', 'login_time')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('user', 'ip_address', 'user_agent', 'login_time', 'success', 'failure_reason')
    date_hierarchy = 'login_time'
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'
    
    def get_status_badge(self, obj):
        if obj.success:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Success</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">Failed</span>'
            )
    get_status_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False  # Login history is created automatically
    
    def has_delete_permission(self, request, obj=None):
        return False  # Don't allow deletion of login history


@admin.register(PasswordChangeHistory)
class PasswordChangeHistoryAdmin(admin.ModelAdmin):
    """Admin interface for PasswordChangeHistory model"""
    list_display = ('get_username', 'ip_address', 'changed_at')
    list_filter = ('changed_at',)
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('user', 'ip_address', 'changed_at')
    date_hierarchy = 'changed_at'
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'
    
    def has_add_permission(self, request):
        return False  # Password changes are logged automatically
    
    def has_delete_permission(self, request, obj=None):
        return False  # Don't allow deletion of password history

