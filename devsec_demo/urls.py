from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # CORRECT: No extra '.admin' here
    path('admin/', admin.site.urls),
    
    # This connects to your accounts app
    path('accounts/', include('accounts.urls')),
    
    # This makes 127.0.0.1:8000 work
    path('', include('accounts.urls')), 
]