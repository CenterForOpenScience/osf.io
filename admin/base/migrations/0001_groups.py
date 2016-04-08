# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.contrib.auth.models import Group
import logging

logger = logging.getLogger(__file__)


def add_groups(*args):
    group, created = Group.objects.get_or_create(name='prereg_group')
    if created:
        logger.info('prereg_group created')
    group, created = Group.objects.get_or_create(name='osf_admin')
    if created:
        logger.info('osf_admin group created')
    group, created = Group.objects.get_or_create(name='osf_group')
    if created:
        logger.info('osf_group created')


class Migration(migrations.Migration):

    operations = [
        migrations.RunPython(add_groups),
    ]
