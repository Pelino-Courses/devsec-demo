from django.contrib import admin
from django.utils.html import format_html
from .models import UserProfile, LoginHistory, PasswordChangeHistory, AuditLog


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


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model - comprehensive security audit trail."""
    
    list_display = ('get_event_type', 'get_user', 'get_severity_badge', 'timestamp', 'ip_address')
    list_filter = ('event_type', 'severity', 'timestamp')
    search_fields = ('user__username', 'affected_user__username', 'ip_address', 'description')
    readonly_fields = ('user', 'affected_user', 'event_type', 'severity', 'ip_address', 
                       'user_agent', 'description', 'details', 'timestamp')
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Event Information', {
            'fields': ('event_type', 'severity', 'timestamp')
        }),
        ('Users Involved', {
            'fields': ('user', 'affected_user'),
            'description': 'user: who triggered the event; affected_user: who was affected by it'
        }),
        ('Request Details', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Event Details', {
            'fields': ('description', 'details'),
        }),
    )
    
    def get_event_type(self, obj):
        """Display event type with color coding."""
        event_name = obj.get_event_type_display()
        
        # Color code by category
        if 'LOGIN' in obj.event_type:
            color = '#007bff'  # Blue
        elif 'PASSWORD' in obj.event_type:
            color = '#dc3545'  # Red
        elif 'ADMIN' in obj.event_type:
            color = '#ff6600'  # Orange
        elif 'REGISTRATION' in obj.event_type:
            color = '#28a745'  # Green
        else:
            color = '#6c757d'  # Gray
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, event_name
        )
    get_event_type.short_description = 'Event Type'
    
    def get_user(self, obj):
        """Display user who triggered the event."""
        if obj.user:
            return f"{obj.user.username} (ID: {obj.user.id})"
        return "Anonymous/System"
    get_user.short_description = 'Triggered By'
    
    def get_severity_badge(self, obj):
        """Display severity with color coding."""
        color_map = {
            'LOW': '#28a745',      # Green
            'MEDIUM': '#ffc107',   # Yellow
            'HIGH': '#fd7e14',     # Orange
            'CRITICAL': '#dc3545', # Red
        }
        
        color = color_map.get(obj.severity, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_severity_display()
        )
    get_severity_badge.short_description = 'Severity'
    
    def has_add_permission(self, request):
        return False  # Audit logs are created automatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Audit logs should not be modified (immutable)
    
    def has_delete_permission(self, request, obj=None):
        return False  # Audit logs should not be deleted (compliance)

