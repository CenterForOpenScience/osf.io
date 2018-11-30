# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

V2_INVISIBLE_SCHEMAS = [
    'RIDIE Registration - Study Complete',
    'RIDIE Registration - Study Initiation',
    'EGAP Project',
    'Confirmatory - General',
]

def remove_version_1_schemas(state, schema):
    RegistrationSchema = state.get_model('osf', 'registrationschema')
    assert RegistrationSchema.objects.filter(schema_version=1, abstractnode__isnull=False).count() == 0
    assert RegistrationSchema.objects.filter(schema_version=1, draftregistration__isnull=False).count() == 0
    RegistrationSchema.objects.filter(schema_version=1).delete()

def set_invisible_schemas(state, schema):
    RegistrationSchema = state.get_model('osf', 'registrationschema')
    RegistrationSchema.objects.filter(name__in=V2_INVISIBLE_SCHEMAS).update(visible=False)

def unset_invisible_schemas(state, schema):
    RegistrationSchema = state.get_model('osf', 'registrationschema')
    RegistrationSchema.objects.filter(name__in=V2_INVISIBLE_SCHEMAS).update(visible=True)

def noop(*args, **kwargs):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0146_add_visible_to_registrationschema'),
    ]

    operations = [
        migrations.RunPython(remove_version_1_schemas, noop),
        migrations.RunPython(set_invisible_schemas, unset_invisible_schemas),
    ]
