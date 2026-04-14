from django.contrib import admin
from .models import Profile, LoginAttempt


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio')


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('username', 'attempts', 'locked_until', 'last_attempt')
    actions = ['unlock_accounts']

    def unlock_accounts(self, request, queryset):
        queryset.update(attempts=0, locked_until=None)
    unlock_accounts.short_description = 'Unlock selected accounts'
