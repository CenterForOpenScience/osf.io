# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from osf.utils.migrations import UpdateRegistrationSchemas



class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0145_add_visible_to_registrationschema'),
    ]

    operations = [
    ]
