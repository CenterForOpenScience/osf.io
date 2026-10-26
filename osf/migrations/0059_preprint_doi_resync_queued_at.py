from django.db import migrations
import osf.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0058_preprint_deleted_spam_created_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='preprint',
            name='doi_resync_queued_at',
            field=osf.utils.fields.NonNaiveDateTimeField(default=None, null=True, blank=True),
        ),
    ]
