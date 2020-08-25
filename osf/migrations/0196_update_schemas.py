from __future__ import unicode_literals

from django.db import migrations
from osf.utils.migrations import UpdateRegistrationSchemasAndSchemaBlocks

def make_egap_active_but_invisible(state, schema):
        RegistrationSchema = state.get_model('osf', 'registrationschema')
        egap_registration = RegistrationSchema.objects.get(name='EGAP Registration', schema_version=2)
        egap_registration.visible = False
        egap_registration.active = True
        egap_registration.save()

def noop(*args, **kwargs):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0195_add_enable_chronos_waffle_flag'),
    ]

    operations = [
        UpdateRegistrationSchemasAndSchemaBlocks(),
        migrations.RunPython(make_egap_active_but_invisible, noop),
    ]
