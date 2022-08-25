# -*- coding: utf-8 -*-
import inspect  # noqa
import logging  # noqa
import jsonschema
import requests
import json  # noqa

from rest_framework import status as http_status

from addons.base.institutions_utils import KEYNAME_BASE_FOLDER
from addons.nextcloudinstitutions import KEYNAME_NOTIFICATION_SECRET
from addons.nextcloudinstitutions.models import NextcloudInstitutionsProvider
from addons.osfstorage.models import Region
from admin.rdm_custom_storage_location.utils import (
    use_https,
    test_dropboxbusiness_connection,
    test_owncloud_connection,
    test_s3_connection,
    test_s3compat_connection,
    wd_info_for_institutions,
)
from osf.models import ExportDataLocation
from website.util import inspect_info  # noqa
from api.base.utils import waterbutler_api_url_for
from admin.base.schemas.utils import from_json

logger = logging.getLogger(__name__)

__all__ = [
    'update_storage_location',
    'save_s3_credentials',
    'save_s3compat_credentials',
    'save_dropboxbusiness_credentials',
    'save_basic_storage_institutions_credentials_common',
    'save_nextcloudinstitutions_credentials',
]


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


def save_dropboxbusiness_credentials(institution, storage_name, provider_name):
    test_connection_result = test_dropboxbusiness_connection(institution)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    wb_credentials, wb_settings = wd_info_for_institutions(provider_name)
    storage_location = update_storage_location(institution.guid, storage_name, wb_credentials, wb_settings)

    return ({
                'message': 'Dropbox Business was set successfully!!'
            }, http_status.HTTP_200_OK)


def save_basic_storage_institutions_credentials_common(institution, storage_name, folder, provider_name, provider, separator=':', extended_data=None):
    """Don't need external account, save all to waterbutler_settings"""
    external_account = {
        'display_name': provider.username,
        'oauth_key': provider.password,
        'oauth_secret': provider.host,
        'provider_id': '{}{}{}'.format(provider.host, separator, provider.username),
        'profile_url': provider.host,
        'provider': provider.short_name,
        'provider_name': provider.name,
    }
    extended = {
        KEYNAME_BASE_FOLDER: folder,
    }
    if type(extended_data) is dict:
        extended.update(extended_data)

    wb_credentials, wb_settings = wd_info_for_institutions(provider_name)
    wb_settings["external_account"] = external_account
    wb_settings["extended"] = extended

    storage_location = update_storage_location(institution.guid, storage_name, wb_credentials, wb_settings)

    return ({
                'message': 'Saved credentials successfully!!'
            }, http_status.HTTP_200_OK)


def save_nextcloudinstitutions_credentials(institution, storage_name, host_url, username, password, folder, notification_secret, provider_name):
    test_connection_result = test_owncloud_connection(host_url, username, password, folder, provider_name)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    host = use_https(host_url)
    # init with an ExternalAccount instance as account
    provider = NextcloudInstitutionsProvider(
        account=None, host=host.url,
        username=username, password=password
    )

    extended_data = {
        KEYNAME_NOTIFICATION_SECRET: notification_secret
    }

    return save_basic_storage_institutions_credentials_common(institution, storage_name, folder, provider_name, provider, extended_data=extended_data)


def process_data_infomation(list_data):
    list_data_version = []
    for item in list_data:
        for file_version in item['version']:
            current_data = {**item}
            current_data['version'] = file_version
            current_data['tags'] = ', '.join(item['tags'])
            list_data_version.append(current_data)
    return list_data_version


def get_list_file_detail(data, pid, provider, request_cookie, guid, process_start):
    data_json = None
    status_code = 0
    for file_info in data:
        if file_info['attributes']['name'] == 'file_info_{}_{}.json'.format(guid, process_start):
            try:
                url = waterbutler_api_url_for(
                    pid, provider, path=file_info['id'].replace(provider, ''), _internal=True
                )
                response = requests.get(
                    url,
                    cookies=request_cookie,
                    stream=True,
                )
            except Exception:
                return None, status_code
            status_code = response.status_code
            if status_code == 200:
                data_json = response.json()
            response.close()
            break
    try:
        schema = from_json('export-data.json')
        jsonschema.validate(data_json, schema)
    except jsonschema.ValidationError:
        # raise e
        return None, 555
    return data_json, status_code


def get_list_file_info(pid, provider, path, request_cookie, guid=None, process_start=None):
    content = None
    status_code = 0
    response = None
    try:
        url = waterbutler_api_url_for(
            pid, provider, path=path, _internal=True, meta=''
        )
        response = requests.get(
            url,
            headers={'content-type': 'application/json'},
            cookies=request_cookie,
        )
    except Exception:
        return None, response.status_code
    status_code = response.status_code
    if response.status_code == 200:
        content = response.json()
        print(content['data'][0]['links'])
    response.close()
    if status_code != 200:
        return None, status_code
    return get_list_file_detail(content['data'], pid, provider, request_cookie, guid, process_start)


def get_link_delete_export_data(pid, provider, path, request_cookie):
    content = None
    status_code = 0
    response = None
    try:
        url = waterbutler_api_url_for(
            pid, provider, path=path, _internal=True, meta=''
        )
        response = requests.get(
            url,
            headers={'content-type': 'application/json'},
            cookies=request_cookie,
        )
    except Exception:
        return None, response.status_code
    status_code = response.status_code
    if response.status_code == 200:
        content = response.json()
    response.close()
    return content['data'], status_code


def is_add_on_storage(waterbutler_settings):
    destination_region = Region.objects.filter(id=destination_id)
    destination_settings = destination_region.values_list("waterbutler_settings", flat=True)[0]
    folder = waterbutler_settings["storage"]["folder"]
    try:
        folder_json = json.loads(folder)
        if not folder_json["encrypt_uploads"]:
            # If folder does not have "encrypt_uploads" then it is add-on storage
            return True
        # If folder has "encrypt_uploads" key and it is set to True then it is bulk-mounted storage
        return False
    except ValueError as e:
        # Cannot parse folder as json, storage is add-on storage
        return True


def check_storage_type(storage_id):
    region = Region.objects.filter(id=storage_id)
    settings = region.values_list("waterbutler_settings", flat=True)[0]
    return is_add_on_storage(settings)
