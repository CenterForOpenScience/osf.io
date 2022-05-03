from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0201_add_egap_flag'),
    ]

    operations = [
        migrations.AddField(
            model_name='abstractprovider',
            name='in_sloan_study',
            field=models.NullBooleanField(default=True),
        ),
        migrations.AddField(
            model_name='preprint',
            name='conflict_of_interest_statement',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='preprint',
            name='data_links',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.URLField(blank=True, null=True),
                                                            blank=True, null=True, size=None),
        ),
        migrations.AddField(
            model_name='preprint',
            name='has_coi',
            field=models.NullBooleanField(),
        ),
        migrations.AddField(
            model_name='preprint',
            name='has_data_links',
            field=models.NullBooleanField(),
        ),
        migrations.AddField(
            model_name='preprint',
            name='has_prereg_links',
            field=models.NullBooleanField(),
        ),
        migrations.AddField(
            model_name='preprint',
            name='prereg_link_info',
            field=models.TextField(blank=True, choices=[('prereg_designs', 'Pre-registration of study designs'),
                                                        ('prereg_analysis', 'Pre-registration of study analysis'), (
                                                        'prereg_both',
                                                        'Pre-registration of study designs and study analysis')],
                                   null=True),
        ),
        migrations.AddField(
            model_name='preprint',
            name='prereg_links',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.URLField(blank=True, null=True),
                                                            blank=True, null=True, size=None),
        ),
        migrations.AddField(
            model_name='preprint',
            name='why_no_data',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='preprint',
            name='why_no_prereg',
            field=models.TextField(blank=True, null=True),
        ),
    ]
