# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from waffle.models import Switch
from osf.features import ENABLE_INACTIVE_SCHEMAS


def add_waffle_switch(*args, **kwargs):
    switch = Switch(name=ENABLE_INACTIVE_SCHEMAS, active=False)
    switch.save()

def remove_waffle_switch(*args, **kwargs):
    switch = Switch.objects.get(name=ENABLE_INACTIVE_SCHEMAS)
    switch.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0143_merge_20181115_1458'),
    ]

    operations = [
        migrations.RunPython(add_waffle_switch, remove_waffle_switch)
    ]
