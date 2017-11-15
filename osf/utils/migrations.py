import os
import json
import logging

from contextlib import contextmanager

from website import settings
from osf.models import NodeLicense, MetaSchema
from website.project.metadata.schemas import OSF_META_SCHEMAS

logger = logging.getLogger(__file__)


@contextmanager
def disable_auto_now_fields(model):
    """
    Context manager to disable updates of all auto_now fields for a given model.

    """
    for field in model._meta.get_fields():
        if hasattr(field, 'auto_now') and field.auto_now:
            field.auto_now = False
    try:
        yield
    finally:
        for field in model._meta.get_fields():
            if hasattr(field, 'auto_now') and not field.auto_now:
                field.auto_now = True


def ensure_licenses(*args, **kwargs):
    """Upsert the licenses in our database based on a JSON file.

    :return tuple: (number inserted, number updated)

    Moved from website/project/licenses/__init__.py
    """
    ninserted = 0
    nupdated = 0
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

            node_license, created = NodeLicense.objects.get_or_create(license_id=id)

            node_license.name = name
            node_license.text = text
            node_license.properties = properties
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
    for schema in OSF_META_SCHEMAS:
        schema_obj, created = MetaSchema.objects.update_or_create(
            name=schema['name'],
            schema_version=schema.get('version', 1),
            defaults={
                'schema': schema,
                'active': schema.get('active', True)
            }
        )
        schema_count += 1

        if created:
            logger.info('Added schema {} to the database'.format(schema['name']))

    logger.info('Ensured {} schemas are in the database'.format(schema_count))


def remove_schemas(*args):
    pre_count = MetaSchema.objects.all().count()
    MetaSchema.objects.all().delete()

    logger.info('Removed {} schemas from the database'.format(pre_count))
