from django.contrib import admin
from django.contrib.auth.models import User
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for UserProfile model.
    
    Features:
    - Display connected User information
    - List filtering by date created
    - Search by student_id and user email/username
    - Readonly fields for audit tracking
    """
    
    list_display = ('get_username', 'student_id', 'get_email', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('student_id', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Student Information', {
            'fields': ('student_id', 'phone_number', 'date_of_birth', 'bio')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_username(self, obj):
        """Display the username from related User object."""
        return obj.user.username
    get_username.short_description = 'Username'
    
    def get_email(self, obj):
        """Display the email from related User object."""
        return obj.user.email
    get_email.short_description = 'Email'
    
    def has_add_permission(self, request):
        """Prevent direct creation of UserProfile (must be created through registration)."""
        return False

