# Generated by Django 3.2.17 on 2024-05-15 15:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0020_abstractprovider_advertise_on_discover_page'),
    ]

    operations = [
        migrations.AddField(
            model_name='preprint',
            name='custom_publication_citation',
            field=models.TextField(blank=True, null=True),
        ),
    ]
