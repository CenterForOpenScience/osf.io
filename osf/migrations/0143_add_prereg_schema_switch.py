# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations
from waffle.models import Switch

from osf.utils.migrations import ensure_schemas
from osf.features import OSF_PREREGISTRATION


def add_prereg_switch(*args, **kwargs):
    switch = Switch(name=OSF_PREREGISTRATION, active=False)
    switch.save()
    ensure_schemas()


def remove_prereg_switch(*args, **kwargs):
    Switch.objects.get(name=OSF_PREREGISTRATION).delete()
    ensure_schemas()


class Migration(migrations.Migration):
    dependencies = [
        ('osf', '0142_remove_waffle_analytics_flags'),
    ]
    operations = [
        migrations.RunPython(add_prereg_switch, remove_prereg_switch)
    ]
