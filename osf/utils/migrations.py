import os
import itertools
import json
import logging
import warnings

from contextlib import contextmanager
from django.apps import apps
from django.db.migrations.operations.base import Operation

from website import settings
from osf.models import NodeLicense, RegistrationSchema
from website.project.metadata.schemas import OSF_META_SCHEMAS

logger = logging.getLogger(__file__)


def get_osf_models():
    """
    Helper function to retrieve all osf related models.

    Example usage:
        with disable_auto_now_fields(models=get_osf_models()):
            ...
    """
    return list(itertools.chain(*[app.get_models() for app in apps.get_app_configs() if app.label.startswith('addons_') or app.label.startswith('osf')]))

@contextmanager
def disable_auto_now_fields(models=None):
    """
    Context manager to disable auto_now field updates.
    If models=None, updates for all auto_now fields on *all* models will be disabled.

    :param list models: Optional list of models for which auto_now field updates should be disabled.
    """
    if not models:
        models = apps.get_models()

    changed = []
    for model in models:
        for field in model._meta.get_fields():
            if hasattr(field, 'auto_now') and field.auto_now:
                field.auto_now = False
                changed.append(field)
    try:
        yield
    finally:
        for field in changed:
            if hasattr(field, 'auto_now') and not field.auto_now:
                field.auto_now = True

@contextmanager
def disable_auto_now_add_fields(models=None):
    """
    Context manager to disable auto_now_add field updates.
    If models=None, updates for all auto_now_add fields on *all* models will be disabled.

    :param list models: Optional list of models for which auto_now_add field updates should be disabled.
    """
    if not models:
        models = apps.get_models()

    changed = []
    for model in models:
        for field in model._meta.get_fields():
            if hasattr(field, 'auto_now_add') and field.auto_now_add:
                field.auto_now_add = False
                changed.append(field)
    try:
        yield
    finally:
        for field in changed:
            if hasattr(field, 'auto_now_add') and not field.auto_now_add:
                field.auto_now_add = True

def ensure_licenses(*args, **kwargs):
    """Upsert the licenses in our database based on a JSON file.

    :return tuple: (number inserted, number updated)

    Moved from website/project/licenses/__init__.py
    """
    ninserted = 0
    nupdated = 0
    try:
        NodeLicense = args[0].get_model('osf', 'nodelicense')
    except Exception:
        # Working outside a migration
        from osf.models import NodeLicense
    with open(
            os.path.join(
                settings.APP_PATH,
                'node_modules', '@centerforopenscience', 'list-of-licenses', 'dist', 'list-of-licenses.json'
            )
    ) as fp:
        licenses = json.loads(fp.read())
        for id, info in licenses.items():
            name = info['name']
            text = info['text']
            properties = info.get('properties', [])
            url = info.get('url', '')

            node_license, created = NodeLicense.objects.get_or_create(license_id=id)

            node_license.name = name
            node_license.text = text
            node_license.properties = properties
            node_license.url = url
            node_license.save()

            if created:
                ninserted += 1
            else:
                nupdated += 1

            logger.info('License {name} ({id}) added to the database.'.format(name=name, id=id))

    logger.info('{} licenses inserted into the database, {} licenses updated in the database.'.format(
        ninserted, nupdated
    ))

    return ninserted, nupdated


def remove_licenses(*args):
    pre_count = NodeLicense.objects.all().count()
    NodeLicense.objects.all().delete()

    logger.info('{} licenses removed from the database.'.format(pre_count))


def ensure_schemas(*args):
    """Import meta-data schemas from JSON to database if not already loaded
    """
    schema_count = 0
    try:
        RegistrationSchema = args[0].get_model('osf', 'registrationschema')
    except Exception:
        try:
            RegistrationSchema = args[0].get_model('osf', 'metaschema')
        except Exception:
            # Working outside a migration
            from osf.models import RegistrationSchema
    for schema in OSF_META_SCHEMAS:
        schema_obj, created = RegistrationSchema.objects.update_or_create(
            name=schema['name'],
            schema_version=schema.get('version', 1),
            defaults={
                'schema': schema,
            }
        )
        schema_count += 1

        if created:
            logger.info('Added schema {} to the database'.format(schema['name']))

    logger.info('Ensured {} schemas are in the database'.format(schema_count))


def remove_schemas(*args):
    pre_count = RegistrationSchema.objects.all().count()
    RegistrationSchema.objects.all().delete()

    logger.info('Removed {} schemas from the database'.format(pre_count))


class UpdateRegistrationSchemas(Operation):
    """Custom migration operation to update registration schemas
    """
    reversible = True

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        ensure_schemas(to_state.apps)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        warnings.warn('Reversing UpdateRegistrationSchemas is a noop')

    def describe(self):
        return 'Updated registration schemas'


class AddWaffleFlags(Operation):
    """Custom migration operation to add waffle flags

    Params:
    - flag_names: iterable of strings, flag names to create
    - on_for_everyone: boolean (default False), whether to activate the newly created flags
    """
    reversible = True

    def __init__(self, flag_names, on_for_everyone=False):
        self.flag_names = flag_names
        self.on_for_everyone = on_for_everyone

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        Flag = to_state.apps.get_model('waffle', 'flag')
        for flag_name in self.flag_names:
            Flag.objects.get_or_create(name=flag_name, defaults={'everyone': self.on_for_everyone})

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        Flag = to_state.apps.get_model('waffle', 'flag')
        Flag.objects.filter(name__in=self.flag_names).delete()

    def describe(self):
        return 'Adds waffle flags: {}'.format(', '.join(self.flag_names))


class DeleteWaffleFlags(Operation):
    """Custom migration operation to delete waffle flags

    Params:
    - flag_names: iterable of strings, flag names to delete
    """
    reversible = True

    def __init__(self, flag_names):
        self.flag_names = flag_names

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        Flag = to_state.apps.get_model('waffle', 'flag')
        Flag.objects.filter(name__in=self.flag_names).delete()

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        Flag = to_state.apps.get_model('waffle', 'flag')
        for flag_name in self.flag_names:
            Flag.objects.get_or_create(name=flag_name)

    def describe(self):
        return 'Removes waffle flags: {}'.format(', '.join(self.flag_names))


class AddWaffleSwitches(Operation):
    """Custom migration operation to add waffle switches

    Params:
    - switch_names: iterable of strings, the names of the switches to create
    - active: boolean (default False), whether the switches should be active
    """
    reversible = True

    def __init__(self, switch_names, active=False):
        self.switch_names = switch_names
        self.active = active

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        Switch = to_state.apps.get_model('waffle', 'switch')
        for switch in self.switch_names:
            Switch.objects.get_or_create(name=switch, defaults={'active': self.active})

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        Switch = to_state.apps.get_model('waffle', 'switch')
        Switch.objects.filter(name__in=self.switch_names).delete()

    def describe(self):
        return 'Adds waffle switches: {}'.format(', '.join(self.switch_names))
