from __future__ import unicode_literals

import logging

from django.contrib.postgres.fields import JSONField
from django.db import migrations, transaction
from django.apps import apps
from django.db.models import Func, F, Value

from addons.osfstorage.settings import DEFAULT_REGION_ID

logger = logging.getLogger(__name__)


def add_storage_type_to_existing_regions(*args):
    """ Add waterbutler_settings['storage']['type'] to current regions """
    Region = apps.get_model('addons_osfstorage', 'Region')

    nii_storage_regions_ids = []
    institution_storage_regions_ids = []

    # Get default region's settings
    default_region = Region.objects.get(_id=DEFAULT_REGION_ID)
    default_region_name = default_region.name
    default_region_credentials = default_region.waterbutler_credentials
    default_region_settings = default_region.waterbutler_settings

    for region in Region.objects.all():
        # Get current region's settings
        region_name = region.name
        waterbutler_credentials = region.waterbutler_credentials
        waterbutler_settings = region.waterbutler_settings

        if region_name == default_region_name and waterbutler_credentials == default_region_credentials and waterbutler_settings == default_region_settings:
            # If storage is using same settings as the NII Storage, add to nii_storage_regions_ids
            nii_storage_regions_ids.append(region.id)
        else:
            # Otherwise, add to institution_storage_regions_ids
            institution_storage_regions_ids.append(region.id)

    try:
        with transaction.atomic():
            # Add type = 'NII_STORAGE' to storages that are using NII Storage
            Region.objects.filter(id__in=nii_storage_regions_ids).update(
                waterbutler_settings=Func(
                    F('waterbutler_settings'),
                    Value(['storage', 'type']),
                    Value(Region.NII_STORAGE, JSONField()),
                    True,
                    function='jsonb_set',
                )
            )

            # Add type = 'INSTITUTIONS' to storages that are not using NII Storage
            Region.objects.filter(id__in=institution_storage_regions_ids).update(
                waterbutler_settings=Func(
                    F('waterbutler_settings'),
                    Value(['storage', 'type']),
                    Value(Region.INSTITUTIONS, JSONField()),
                    True,
                    function='jsonb_set',
                )
            )
    except Exception as e:
        # Transaction failed, log error and raise exception
        logger.error(f'Adding storage type migration failed with error {e}')
        raise e


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0232_auto_20230830_0425'),
    ]

    operations = [
        migrations.RunPython(add_storage_type_to_existing_regions, migrations.RunPython.noop),
    ]
