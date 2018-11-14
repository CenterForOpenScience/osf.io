# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations
from waffle.models import Switch


def add_prereg_switch(*args, **kwargs):
    switch = Switch(name='osf_preregistration', active=False)
    switch.save()


def remove_prereg_switch(*args, **kwargs):
    Switch.objects.get(name='osf_preregistration').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('osf', '0142_remove_waffle_analytics_flags'),
    ]
    operations = [
        migrations.RunPython(add_prereg_switch, remove_prereg_switch)
    ]
