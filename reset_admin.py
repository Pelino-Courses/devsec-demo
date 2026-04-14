import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devsec_demo.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

admin = User.objects.get(username='admin')
admin.set_password('Admin@12345')
admin.is_staff = True
admin.is_superuser = True
admin.is_active = True
admin.save()
print('✅ Admin account configured:')
print(f'   Username: admin')
print(f'   Password: Admin@12345')
print(f'   is_staff: {admin.is_staff}')
print(f'   is_superuser: {admin.is_superuser}')
print(f'   is_active: {admin.is_active}')
