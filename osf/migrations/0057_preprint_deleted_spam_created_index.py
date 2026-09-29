from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('osf', '0056_merge_20260918'),
    ]

    operations = [
        AddIndexConcurrently(
            model_name='preprint',
            index=models.Index(
                fields=['deleted', 'spam_status', 'created'],
                name='preprint_del_spam_created_idx',
            ),
        ),
    ]
