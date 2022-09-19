from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0249_schema_response_justification_to_text_field'),
    ]

    operations = [
        migrations.RenameModel('NotableEmailDomain', 'NotableDomain'),
        migrations.AlterField(
            model_name='notabledomain',
            name='note',
            field=models.IntegerField(choices=[(0, 'EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT'), (1, 'ASSUME_HAM_UNTIL_REPORTED'), (2, 'UNKNOWN'), (3, 'IGNORED')], default=2),
        ),
    ]
