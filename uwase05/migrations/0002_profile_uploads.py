from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('uwase05', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='avatar',
            field=models.FileField(blank=True, null=True, upload_to='uploads/avatars/'),
        ),
        migrations.AddField(
            model_name='profile',
            name='document',
            field=models.FileField(blank=True, null=True, upload_to='uploads/documents/'),
        ),
    ]
