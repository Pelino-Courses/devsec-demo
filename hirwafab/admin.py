from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for UserProfile model.
    Provides easy management of user profiles and their associated data.
    """
    list_display = ('user', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'bio')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Profile Information', {
            'fields': ('bio', 'avatar')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
