from django.db import migrations, models
import ndayishimiye.models


class Migration(migrations.Migration):

    dependencies = [
        ('ndayishimiye', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='avatar',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=ndayishimiye.models.avatar_upload_path,
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='document',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=ndayishimiye.models.document_upload_path,
            ),
        ),
    ]
