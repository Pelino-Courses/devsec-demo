from django.contrib import admin
from .models import Profile, LoginAttempt, AccountLockout


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'created_at']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at']
    list_editable = ['role']


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['username', 'ip_address', 'was_successful', 'timestamp']
    list_filter = ['was_successful', 'timestamp']
    search_fields = ['username', 'ip_address']
    readonly_fields = ['username', 'ip_address', 'was_successful', 'timestamp']


@admin.register(AccountLockout)
class AccountLockoutAdmin(admin.ModelAdmin):
    list_display = ['username', 'locked_until']
    search_fields = ['username']