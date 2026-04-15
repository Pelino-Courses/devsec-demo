from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),  # ✅ keep only this one
    # ❌ Remove the root include — it causes URL conflicts
]