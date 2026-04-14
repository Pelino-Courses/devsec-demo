from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):

    # 🧾 Columns shown in the list page
    list_display = ['id', 'user', 'email', 'created_at', 'is_recent']

    # 🔍 Search functionality
    search_fields = ['user__username', 'user__email']

    # 🎛️ Filters on the right side
    list_filter = ['created_at', 'user__is_active']

    # 📅 Add date navigation at top
    date_hierarchy = 'created_at'

    # ✏️ Make some fields read-only
    readonly_fields = ['created_at']

    # ⚡ Clickable link to edit profile
    list_display_links = ['user']

    # 🧠 Custom methods for extra interactivity
    def email(self, obj):
        return obj.user.email
    email.short_description = "Email"

    def is_recent(self, obj):
        from django.utils import timezone
        return (timezone.now() - obj.created_at).days < 7
    is_recent.boolean = True
    is_recent.short_description = "New (7 days)"