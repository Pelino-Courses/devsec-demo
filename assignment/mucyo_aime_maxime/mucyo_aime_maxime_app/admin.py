from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


class UserAdmin(BaseUserAdmin):
    """Enhanced User admin for authentication management with role display."""
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'get_roles', 'is_active', 'date_joined'
    )
    list_filter = ('is_active', 'date_joined', 'groups')
    search_fields = ('username', 'email')
    filter_horizontal = ('groups',)
    
    def get_roles(self, obj):
        """Display user's roles (groups and staff status)."""
        roles = []
        if obj.is_superuser:
            roles.append('Admin')
        if obj.is_staff:
            roles.append('Staff')
        groups = obj.groups.values_list('name', flat=True)
        roles.extend(groups)
        return ', '.join(roles) if roles else 'User'
    
    get_roles.short_description = 'Roles'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# Configure Group admin
class GroupAdmin(admin.ModelAdmin):
    """Admin interface for managing user groups and permissions."""
    list_display = ('name', 'num_permissions', 'num_users')
    filter_horizontal = ('permissions',)
    
    def num_permissions(self, obj):
        """Display count of permissions for the group."""
        return obj.permissions.count()
    num_permissions.short_description = 'Permissions'
    
    def num_users(self, obj):
        """Display count of users in the group."""
        return obj.user_set.count()
    num_users.short_description = 'Users'


admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)


def create_default_groups():
    """
    Initialize default role groups if they don't exist.
    
    This is called once during app initialization to set up:
    - Staff: can view and manage user dashboard
    - Instructor: can view reports and user activity
    """
    staff_group, created = Group.objects.get_or_create(name='Staff')
    instructor_group, created = Group.objects.get_or_create(name='Instructor')
    
    return staff_group, instructor_group

