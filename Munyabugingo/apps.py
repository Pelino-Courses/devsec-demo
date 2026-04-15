from django.apps import AppConfig
from django.db.models.signals import post_migrate

def create_user_groups(sender, **kwargs):
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType
    from Munyabugingo.models import Profile

    # Create groups
    standard_group, _ = Group.objects.get_or_create(name='Standard Users')
    privileged_group, _ = Group.objects.get_or_create(name='Privileged Users')

    # Assign custom permission to privileged group
    content_type = ContentType.objects.get_for_model(Profile)
    permission, _ = Permission.objects.get_or_create(
        codename='can_view_admin_dashboard',
        content_type=content_type,
        defaults={'name': 'Can view administrative dashboard'}
    )
    privileged_group.permissions.add(permission)


class MunyabugingoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Munyabugingo'

    def ready(self):
        import Munyabugingo.signals
        post_migrate.connect(create_user_groups, sender=self)
