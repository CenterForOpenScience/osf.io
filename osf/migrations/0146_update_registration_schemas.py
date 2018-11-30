# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from osf.utils.migrations import UpdateRegistrationSchemas

V2_INVISIBLE_SCHEMAS = [
    'EGAP Project',
    'OSF Preregistration',
    'Confirmatory - General',
    'RIDIE Registration - Study Complete',
    'RIDIE Registration - Study Initiation',
]

V2_INACTIVE_SCHEMAS = V2_INVISIBLE_SCHEMAS + [
    'Election Research Preacceptance Competition',
]

def remove_version_1_schemas(state, schema):
    RegistrationSchema = state.get_model('osf', 'registrationschema')
    assert RegistrationSchema.objects.filter(schema_version=1, abstractnode__isnull=False).count() == 0
    assert RegistrationSchema.objects.filter(schema_version=1, draftregistration__isnull=False).count() == 0
    RegistrationSchema.objects.filter(schema_version=1).delete()

def update_v2_schemas(state, schema):
    RegistrationSchema = state.get_model('osf', 'registrationschema')
    RegistrationSchema.objects.filter(name__in=V2_INVISIBLE_SCHEMAS).update(visible=False)
    RegistrationSchema.objects.filter(name__in=V2_INACTIVE_SCHEMAS).update(active=False)

def noop(*args, **kwargs):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0145_add_visible_to_registrationschema'),
    ]

    operations = [
        migrations.RunPython(remove_version_1_schemas, noop),
        UpdateRegistrationSchemas(),
        migrations.RunPython(update_v2_schemas, noop),
    ]
