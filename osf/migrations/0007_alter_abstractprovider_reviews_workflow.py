# Generated by Django 3.2.15 on 2022-11-30 16:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0006_collections_moderation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='abstractprovider',
            name='reviews_workflow',
            field=models.CharField(blank=True, choices=[(None, 'None'), ('pre-moderation', 'Pre-Moderation'), ('post-moderation', 'Post-Moderation'), ('semi-moderation', 'Semi-Moderation')], max_length=15, null=True),
        ),
    ]