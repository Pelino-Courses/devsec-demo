from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio_preview')
    search_fields = ('user__username',)

    def bio_preview(self, obj):
        return obj.bio[:60] if obj.bio else '—'
    bio_preview.short_description = 'Bio'
