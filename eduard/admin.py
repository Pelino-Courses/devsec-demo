from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import LoginAttempt, UserProfile

admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('username', 'failed_attempts', 'last_failed_at', 'locked_until')
    list_filter = ('locked_until',)
    search_fields = ('username',)
    readonly_fields = ('username', 'failed_attempts', 'last_failed_at', 'locked_until')

    def has_add_permission(self, request):
        return False


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio')
    search_fields = ('user__username',)