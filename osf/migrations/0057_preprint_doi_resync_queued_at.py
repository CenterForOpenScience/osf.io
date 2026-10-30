from django.db import migrations
import osf.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0056_merge_20260918'),
    ]

    operations = [
        migrations.AddField(
            model_name='preprint',
            name='doi_resync_queued_at',
            field=osf.utils.fields.NonNaiveDateTimeField(default=None, null=True, blank=True),
        ),
    ]
