from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

# Re-register the built-in User model under our app's admin section
# so it's visible and manageable from the admin panel.
admin.site.unregister(User)
admin.site.register(User, UserAdmin)