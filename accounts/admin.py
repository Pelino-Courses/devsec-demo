from django.contrib import admin
from .models import UserProfile, AuditLog

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'event_type', 'user', 'username_attempted', 'ip_address')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('username_attempted', 'details')
    readonly_fields = ('timestamp', 'event_type', 'user', 'username_attempted', 'ip_address', 'details')
