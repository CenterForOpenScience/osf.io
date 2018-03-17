# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.db import migrations
from osf.utils.migrations import ensure_licenses, remove_licenses


logger = logging.getLogger(__file__)


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0084_merge_20180308_1821'),
    ]

    operations = [
        migrations.RunPython(ensure_licenses, remove_licenses),
    ]
