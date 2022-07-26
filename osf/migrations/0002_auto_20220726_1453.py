# Generated by Django 3.2 on 2022-07-26 14:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('addons_osfstorage', '0006_rename_deleted_field'),
        ('osf', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileversion',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='addons_osfstorage.region'),
        ),
        migrations.AddField(
            model_name='preprint',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='addons_osfstorage.region'),
        ),
    ]
