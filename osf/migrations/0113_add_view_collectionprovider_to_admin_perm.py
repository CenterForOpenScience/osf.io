from __future__ import unicode_literals

from django.db import migrations


def noop(*args):
    # This migration used to update admin group perms,
    # This is now handled by the post_migrate signal
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0112_alter_collectionprovider_permissions'),
    ]

    operations = [
        migrations.RunPython(noop, noop),
    ]
