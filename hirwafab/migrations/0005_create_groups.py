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


def create_groups(apps, schema_editor):
    from django.apps import apps as real_apps
    from django.contrib.contenttypes.management import create_contenttypes
    from django.contrib.auth.management import create_permissions

    # In a fresh test database, content types and permissions are not yet
    # populated (they're created by post_migrate signals after all migrations
    # finish). We trigger them explicitly here so the data migration can run.
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


def remove_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=['students', 'instructors']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('hirwafab', '0004_permissions'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]
