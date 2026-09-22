from django.db import migrations
import osf.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0044_notification_scheduled'),
    ]

    operations = [
        migrations.AddField(
            model_name='preprint',
            name='doi_resync_queued_at',
            field=osf.utils.fields.NonNaiveDateTimeField(default=None, null=True, blank=True),
        ),
    ]
