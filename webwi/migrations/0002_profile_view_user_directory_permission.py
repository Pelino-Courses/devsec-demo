from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('webwi', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='profile',
            options={
                'permissions': [('view_user_directory', 'Can view privileged user directory')],
            },
        ),
    ]
