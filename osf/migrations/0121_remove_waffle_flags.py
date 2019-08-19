# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-07-23 13:16
from __future__ import unicode_literals
from waffle.models import Flag
from django.db import migrations


EMBER_WAFFLE_PAGES = [
    'dashboard',
    'home',
]

def format_ember_waffle_flag_name(page):
    return 'ember_{}_page'.format(page)

def add_ember_waffle_flags(state, schema):
    for page in EMBER_WAFFLE_PAGES:
        Flag.objects.get_or_create(name=format_ember_waffle_flag_name(page), everyone=False)
    return

def remove_waffle_flags(state, schema):
    pages = [format_ember_waffle_flag_name(page) for page in EMBER_WAFFLE_PAGES]
    Flag.objects.filter(name__in=pages).delete()
    return


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0120_merge_20180716_1457'),
    ]

    operations = [
        migrations.RunPython(remove_waffle_flags, add_ember_waffle_flags),
    ]
