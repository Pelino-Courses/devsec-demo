from django.db import migrations


STUDENT_PERMS = [
    'view_dashboard',
    'view_own_profile',
    'change_own_profile',
    'change_own_password',
    'view_user_directory',
]

INSTRUCTOR_PERMS = STUDENT_PERMS + [
    'view_all_profiles',
    'view_user_activity',
    'download_reports',
]


def fix_group_permissions(apps, schema_editor):
    from django.apps import apps as real_apps
    from django.contrib.contenttypes.management import create_contenttypes
    from django.contrib.auth.management import create_permissions

    # Ensure permissions exist before assigning (safe to call multiple times)
    app_config = real_apps.get_app_config('hirwafab')
    create_contenttypes(app_config, verbosity=0)
    create_permissions(app_config, verbosity=0)

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    ct = ContentType.objects.get(app_label='hirwafab', model='userprofile')

    students_group, _ = Group.objects.get_or_create(name='students')
    students_group.permissions.set(
        Permission.objects.filter(content_type=ct, codename__in=STUDENT_PERMS)
    )

    instructors_group, _ = Group.objects.get_or_create(name='instructors')
    instructors_group.permissions.set(
        Permission.objects.filter(content_type=ct, codename__in=INSTRUCTOR_PERMS)
    )


class Migration(migrations.Migration):

    dependencies = [
        ('hirwafab', '0005_create_groups'),
    ]

    operations = [
        migrations.RunPython(fix_group_permissions, migrations.RunPython.noop),
    ]
