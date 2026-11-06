from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0060_merge_20261028_1756'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='guid',
            options={
                'get_latest_by': 'created',
                'ordering': ['-created'],
                'permissions': [('remove_guid', 'Can remove and reassign guids')],
            },
        ),
    ]
