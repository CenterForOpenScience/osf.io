# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import connection, migrations, models

def add_custom_mapping_constraint(state, schema):
    sql = """
        ALTER TABLE osf_subject
        ADD CONSTRAINT customs_must_be_mapped
        CHECK (bepress_subject_id IS NOT NULL OR provider_id = %s);
    """
    try:
        osf_id = state.get_model('osf', 'preprintprovider').objects.get(_id='osf').id
    except models.ObjectDoesNotExist:
        # Allow test / local dev DBs to pass
        pass
    else:
        with connection.cursor() as cursor:
            cursor.execute(sql, [osf_id])

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0014_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='subject',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to='osf.Subject')
        ),
        migrations.AddField(
            model_name='subject',
            name='provider',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to='osf.PreprintProvider', related_name='subjects')
        ),
        migrations.AddField(
            model_name='subject',
            name='bepress_subject',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, to='osf.Subject', related_name='aliases')
        ),
        migrations.RunSQL(
            """
            UPDATE osf_subject
            SET provider_id = (SELECT id FROM osf_preprintprovider WHERE _id = 'osf');
            """
        ),
        migrations.RunSQL(
            """
            UPDATE osf_subject
            SET parent_id=subquery.to_subject_id
            FROM (SELECT from_subject_id, to_subject_id
                  FROM  osf_subject_parents) AS subquery
            WHERE osf_subject.id=subquery.from_subject_id;
            """
        ),
        migrations.RunPython(
            add_custom_mapping_constraint
        ),
        migrations.RemoveField(
            model_name='subject',
            name='parents'
        ),
        migrations.AlterField(
            model_name='subject',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to='osf.Subject', related_name='children')
        ),
        migrations.AlterField(
            model_name='subject',
            name='provider',
            field=models.ForeignKey(blank=False, null=False, on_delete=models.deletion.CASCADE, to='osf.PreprintProvider', related_name='subjects')
        ),
    ]
