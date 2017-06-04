# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.contrib.auth.models import Group
import logging

logger = logging.getLogger(__file__)


def add_groups(*args):
    group, created = Group.objects.get_or_create(name='nodes_and_users')
    if created:
        logger.info('nodes_and_users group created')

    try:
        group = Group.objects.get(name='prereg_group')
        group.name = 'prereg'
        group.save()
        logger.info('prereg_group renamed to prereg')
    except Group.DoesNotExist:
        group, created = Group.objects.get_or_create(name='prereg')
        if created:
            logger.info('prereg group created')


def remove_groups(*args):
    Group.objects.filter(name='nodes_and_users').delete()

    group = Group.objects.get(name='prereg')
    group.name = 'prereg_group'
    group.save()


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_groups'),
    ]

    operations = [
        migrations.RunPython(add_groups, remove_groups),
    ]
