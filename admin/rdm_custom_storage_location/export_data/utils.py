# -*- coding: utf-8 -*-
import inspect  # noqa
import logging  # noqa

from rest_framework import status as http_status

from addons.osfstorage.models import Region
from admin.rdm_custom_storage_location.utils import (
    get_addon_by_name, test_s3_connection, test_s3compat_connection
)
from osf.models import ExportDataLocation
from website.util import inspect_info  # noqa

logger = logging.getLogger(__name__)


def update_storage_location(institution_guid, storage_name, wb_credentials, wb_settings):
    try:
        storage_location = ExportDataLocation.objects.get(institution_guid=institution_guid, name=storage_name)
    except ExportDataLocation.DoesNotExist:
        default_region = Region.objects.first()
        storage_location = ExportDataLocation.objects.create(
            institution_guid=institution_guid,
            name=storage_name,
            waterbutler_credentials=wb_credentials,
            waterbutler_settings=wb_settings,
            waterbutler_url=default_region.waterbutler_url,
            mfr_url=default_region.mfr_url,
        )
    else:
        storage_location.name = storage_name
        storage_location.waterbutler_credentials = wb_credentials
        storage_location.waterbutler_settings = wb_settings
        storage_location.save()
    return storage_location


def save_s3_credentials(institution_guid, storage_name, access_key, secret_key, bucket):
    test_connection_result = test_s3_connection(access_key, secret_key, bucket)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    wb_credentials = {
        'storage': {
            'access_key': access_key,
            'secret_key': secret_key,
        },
    }
    wb_settings = {
        'storage': {
            'folder': {
                'encrypt_uploads': True,
            },
            'bucket': bucket,
            'provider': 's3',
        },
    }

    storage_location = update_storage_location(institution_guid, storage_name, wb_credentials, wb_settings)

    return ({
                'message': 'Saved credentials successfully!!'
            }, http_status.HTTP_200_OK)


def save_s3compat_credentials(institution_guid, storage_name, host_url, access_key, secret_key, bucket):
    test_connection_result = test_s3compat_connection(host_url, access_key, secret_key, bucket)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    host = host_url.rstrip('/').replace('https://', '').replace('http://', '')

    wb_credentials = {
        'storage': {
            'access_key': access_key,
            'secret_key': secret_key,
            'host': host,
        }
    }
    wb_settings = {
        'storage': {
            'folder': {
                'encrypt_uploads': True,
            },
            'bucket': bucket,
            'provider': 's3compat',
        }
    }

    storage_location = update_storage_location(institution_guid, storage_name, wb_credentials, wb_settings)

    return ({
                'message': 'Saved credentials successfully!!'
            }, http_status.HTTP_200_OK)


def get_export_location_list(ins_user_id):
    list_location = ExportDataLocation.objects.filter(institution_guid=ins_user_id)
    list_location_dict = []
    for location in list_location:
        waterbutler_settings = location.waterbutler_settings
        provider_name = None
        if "storage" in waterbutler_settings:
            storage = waterbutler_settings["storage"]
            if "provider" in storage:
                provider_name = storage["provider"]
                addon = get_addon_by_name(provider_name)
                provider_name = addon.full_name
        list_location_dict.append({'id': location.id, 'name': location.name, 'provider_name': provider_name})
    return list_location_dict
