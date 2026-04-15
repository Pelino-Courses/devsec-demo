from django.contrib import admin
from django.contrib.auth.models import User, Group
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for UserProfile model with RBAC support.
    """
    list_display = ('get_username', 'student_id', 'get_email', 'get_groups', 'created_at')
    list_filter = ('created_at', 'updated_at', 'user__groups')
    search_fields = ('student_id', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'user')

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
        """Display username."""
        return obj.user.username
    get_username.short_description = 'Username'

    def get_email(self, obj):
        """Display email."""
        return obj.user.email
    get_email.short_description = 'Email'
    
    def get_groups(self, obj):
        """Display user's groups/roles."""
        groups = obj.user.groups.values_list('name', flat=True)
        if groups:
            return ', '.join(groups)
        return '(No role assigned)'
    get_groups.short_description = 'Role(s)'


# Customize the User admin to show group assignments more prominently
class UserGroupInline(admin.TabularInline):
    """Inline for managing groups in User admin."""
    model = User.groups.through
    extra = 0


# Unregister the default Group admin and register our enhanced version
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """Enhanced admin for Group model with permission display."""
    list_display = ('name', 'get_member_count', 'get_permission_count')
    
    def get_member_count(self, obj):
        """Count of users in this group."""
        return obj.user_set.count()
    get_member_count.short_description = 'Members'
    
    def get_permission_count(self, obj):
        """Count of permissions assigned to this group."""
        return obj.permissions.count()
    get_permission_count.short_description = 'Permissions'
