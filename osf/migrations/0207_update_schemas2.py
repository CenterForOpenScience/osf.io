from __future__ import unicode_literals

from django.db import migrations
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks

def make_egap_active_but_invisible(state, schema):
        RegistrationSchema = state.get_model('osf', 'registrationschema')
        new_egap_registration = RegistrationSchema.objects.get(name='EGAP Registration', schema_version=3)
        new_egap_registration.visible = False
        new_egap_registration.active = True
        new_egap_registration.save()

def noop(*args, **kwargs):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0207_ensure_schemas'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
        migrations.RunPython(make_egap_active_but_invisible, noop),
    ]
