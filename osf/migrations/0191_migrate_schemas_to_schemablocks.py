# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-09-26 20:08
from __future__ import unicode_literals

import logging
from django.db import migrations
from osf.utils.migrations import map_schemas_to_schemablocks

logger = logging.getLogger(__file__)

def remove_version_1_schemas(state, schema):
    RegistrationSchema = state.get_model('osf', 'registrationschema')
    assert RegistrationSchema.objects.filter(schema_version=1, abstractnode__isnull=False).count() == 0
    assert RegistrationSchema.objects.filter(schema_version=1, draftregistration__isnull=False).count() == 0
    RegistrationSchema.objects.filter(schema_version=1).delete()

def update_schemaless_registrations(state, schema):
    RegistrationSchema = state.get_model('osf', 'registrationschema')
    AbstractNode = state.get_model('osf', 'abstractnode')

    open_ended_schema = RegistrationSchema.objects.get(name='Open-Ended Registration', schema_version=2)
    open_ended_meta = {
        '{}'.format(open_ended_schema._id): {
            'summary': {
                'comments': [],
                'extra': [],
                'value': ''
            }
        }
    }

    schemaless_regs_with_meta = AbstractNode.objects.filter(type='osf.registration', registered_schema__isnull=True).exclude(registered_meta={})
    schemaless_regs_without_meta = AbstractNode.objects.filter(type='osf.registration', registered_schema__isnull=True, registered_meta={})

    for reg in schemaless_regs_without_meta.all():
        reg.registered_schema.add(open_ended_schema)
        reg.registered_meta = open_ended_meta
        reg.save()

    for reg in schemaless_regs_with_meta.all():
        reg.registered_schema.add(RegistrationSchema.objects.get(_id=reg.registered_meta.keys()[0]))

def update_schema_configs(state, schema):
    RegistrationSchema = state.get_model('osf', 'registrationschema')
    for rs in RegistrationSchema.objects.all():
        if rs.schema.get('description', False):
            rs.description = rs.schema['description']
        if rs.schema.get('config', False):
            rs.config = rs.schema['config']
        rs.save()

def unset_schema_configs(state, schema):
    RegistrationSchema = state.get_model('osf', 'registrationschema')
    RegistrationSchema.objects.update(
        config=dict(),
        description='',
    )


def noop(*args, **kwargs):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0190_add_schema_block_models')
    ]

    operations = [
        migrations.RunPython(remove_version_1_schemas, noop),
        migrations.RunPython(update_schemaless_registrations, noop),
        migrations.RunPython(update_schema_configs, unset_schema_configs),
        migrations.RunPython(map_schemas_to_schemablocks, migrations.RunPython.noop)
    ]
