# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from waffle.models import Switch

from osf.utils.migrations import ensure_schemas
from osf.features import OSF_PREREGISTRATION


def add_prereg_switch(*args, **kwargs):
    switch = Switch(name=OSF_PREREGISTRATION, active=False)
    switch.save()

def remove_prereg_switch(*args, **kwargs):
    Switch.objects.get(name=OSF_PREREGISTRATION).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0144_enable_inactive_schemas_switch'),
    ]

    operations = [
        migrations.RunPython(add_prereg_switch, remove_prereg_switch),
        migrations.RunPython(ensure_schemas, ensure_schemas),
    ]
