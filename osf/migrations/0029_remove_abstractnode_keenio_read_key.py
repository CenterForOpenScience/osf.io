# Generated by Django 4.2.15 on 2025-02-21 13:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0028_collection_grade_levels_choices_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='abstractnode',
            name='keenio_read_key',
        ),
    ]
