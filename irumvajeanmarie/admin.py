from django.contrib import admin
from .models import Profile, LoginAttempt, AccountLockout, ContactMessage
import logging

logger = logging.getLogger('irumvajeanmarie.audit')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'created_at']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at']
    list_editable = ['role']

    def save_model(self, request, obj, form, change):
        if change and 'role' in form.changed_data:
            try:
                old_obj = self.model.objects.get(pk=obj.pk)
                if old_obj.role != obj.role:
                    logger.info(f"Role change: changed_by={request.user.username}, target_user={obj.user.username}, old_role={old_obj.role}, new_role={obj.role}")
            except self.model.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)


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


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    search_fields = ['user__username', 'message']
    readonly_fields = ['created_at']