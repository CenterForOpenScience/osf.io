from __future__ import unicode_literals

from django.db import migrations


def noop(*args, **kwargs):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0207_ensure_schemas'),
    ]

    operations = []
