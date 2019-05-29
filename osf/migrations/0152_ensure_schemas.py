from __future__ import unicode_literals

from django.db import migrations
from osf.utils.migrations import ensure_schemas


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0151_auto_20181215_1911'),
    ]

    operations = [
        migrations.RunPython(ensure_schemas, ensure_schemas),
    ]
