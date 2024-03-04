# -*- coding: utf-8 -*-
import inspect  # noqa
import json  # noqa
import logging  # noqa
from copy import deepcopy

import jsonschema
import requests
import hashlib
from django.db import transaction
from django.db.models import Q
from rest_framework import status as http_status

from addons.base.institutions_utils import KEYNAME_BASE_FOLDER
from addons.dropboxbusiness import utils as dropboxbusiness_utils
from addons.metadata.models import FileMetadata
from addons.nextcloudinstitutions import KEYNAME_NOTIFICATION_SECRET
from addons.nextcloudinstitutions.models import NextcloudInstitutionsProvider
from addons.osfstorage.models import Region
from admin.base.schemas.utils import from_json
from admin.rdm_custom_storage_location.utils import (
    use_https,
    test_owncloud_connection,
    test_s3_connection,
    test_s3compat_connection,
    wd_info_for_institutions,
)
from api.base.utils import waterbutler_api_url_for
from osf.models import (
    ExportData,
    ExportDataRestore,
    ExportDataLocation,
    ExternalAccount,
    BaseFileNode,
    AbstractNode,
)
from website.settings import (
    WATERBUTLER_URL,
    INSTITUTIONAL_STORAGE_ADD_ON_METHOD,
    INSTITUTIONAL_STORAGE_BULK_MOUNT_METHOD,
    ADDONS_HAS_MAX_KEYS
)
from website.util import inspect_info  # noqa
from admin.base.settings import EACH_FILE_EXPORT_RESTORE_TIME_OUT

logger = logging.getLogger(__name__)

__all__ = [
    'update_storage_location',
    'save_s3_credentials',
    'save_s3compat_credentials',
    'save_dropboxbusiness_credentials',
    'save_basic_storage_institutions_credentials_common',
    'save_nextcloudinstitutions_credentials',
    'process_data_information',
    'validate_exported_data',
    'write_json_file',
    'check_diff_between_version',
    'count_files_ng_ok',
    'check_for_file_existent_on_export_location',
    'is_add_on_storage',
    'check_file_metadata',
]
ANY_BACKUP_FOLDER_REGEX = '^\\/backup_\\d{8,13}\\/.*$'


def write_json_file(json_data, output_file):
    """Write json data to a file

    Args:
        json_data: data in json or dictionary
        output_file: the full path of output file

    Raises:
        Exception - Exception when writing the file
    """
    with open(output_file, 'w', encoding='utf-8') as write_file:
        try:
            json.dump(json_data, write_file, ensure_ascii=False, indent=2, sort_keys=False)
        except Exception as exc:
            raise Exception(f'Cannot write json file. Exception: {str(exc)}')


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


def test_dropboxbusiness_connection(institution):
    fm = dropboxbusiness_utils.get_two_addon_options(institution.id, allowed_check=False)

    if fm is None:
        message = u'Invalid Institution ID.: {}'.format(institution.id)
        return {'message': message}, http_status.HTTP_400_BAD_REQUEST

    f_option, m_option = fm
    f_token = dropboxbusiness_utils.addon_option_to_token(f_option)
    m_token = dropboxbusiness_utils.addon_option_to_token(m_option)
    if f_token is None or m_token is None:
        return {'message': 'No tokens.'}, http_status.HTTP_400_BAD_REQUEST
    try:
        # use two tokens and connect
        dropboxbusiness_utils.TeamInfo(f_token, m_token, connecttest=True)
        return {'message': 'Credentials are valid', }, http_status.HTTP_200_OK
    except Exception:
        return {'message': 'Invalid tokens.'}, http_status.HTTP_400_BAD_REQUEST


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

    update_storage_location(institution_guid, storage_name, wb_credentials, wb_settings)

    return {'message': 'Saved credentials successfully!!'}, http_status.HTTP_200_OK


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

    update_storage_location(institution_guid, storage_name, wb_credentials, wb_settings)

    return {'message': 'Saved credentials successfully!!'}, http_status.HTTP_200_OK


def save_dropboxbusiness_credentials(institution, storage_name, provider_name):
    test_connection_result = test_dropboxbusiness_connection(institution)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    fm = dropboxbusiness_utils.get_two_addon_options(institution.id)
    if fm is None:
        # Institution has no valid oauth keys.
        return  # disabled

    f_option, m_option = fm
    f_token = dropboxbusiness_utils.addon_option_to_token(f_option)
    m_token = dropboxbusiness_utils.addon_option_to_token(m_option)
    if f_token is None or m_token is None:
        return  # disabled

    # ## ----- enabled -----
    # checking the validity of Dropbox API here
    try:
        team_info = dropboxbusiness_utils.TeamInfo(f_token, m_token, connecttest=True, admin=True, groups=True)
        admin_group, admin_dbmid_list = dropboxbusiness_utils.get_current_admin_group_and_sync(team_info)
        admin_dbmid = dropboxbusiness_utils.get_current_admin_dbmid(m_option, admin_dbmid_list)
        team_folder_id = list(team_info.team_folders.keys())[0]
    except Exception:
        logger.exception('Dropbox Business API Error')
        raise

    wb_credentials, wb_settings = wd_info_for_institutions(provider_name)
    wb_credentials['external_account'] = {
        'fileaccess_token': f_token,
        'management_token': m_token,
    }
    wb_settings['admin_dbmid'] = admin_dbmid
    wb_settings['team_folder_id'] = team_folder_id

    update_storage_location(institution.guid, storage_name, wb_credentials, wb_settings)

    external_account__ids = f_option.external_accounts.all().union(m_option.external_accounts.all()).values_list('id', flat=True)
    f_option.external_accounts.clear()
    f_option.save()
    m_option.external_accounts.clear()
    m_option.save()
    external_accounts = ExternalAccount.objects.filter(pk__in=external_account__ids)
    external_accounts.delete()

    return {'message': 'Dropbox Business was set successfully!!'}, http_status.HTTP_200_OK


def save_basic_storage_institutions_credentials_common(
        institution, storage_name, folder, provider_name, provider,
        separator=':', extended_data=None):
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
    wb_credentials['external_account'] = external_account
    wb_settings['extended'] = extended

    update_storage_location(institution.guid, storage_name, wb_credentials, wb_settings)

    return {'message': 'Saved credentials successfully!!'}, http_status.HTTP_200_OK


def save_nextcloudinstitutions_credentials(
        institution, storage_name, host_url, username, password, folder,
        notification_secret, provider_name):
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

    return save_basic_storage_institutions_credentials_common(
        institution, storage_name, folder, provider_name,
        provider, extended_data=extended_data)


def validate_exported_data(data_json, schema_filename='file-info-schema.json'):
    try:
        schema = from_json(schema_filename)
        jsonschema.validate(data_json, schema)
        return True
    except jsonschema.ValidationError as e:
        logger.error(f'jsonschema.ValidationError: {e}')
        return False


def validate_file_json(file_data, json_schema_file_name):
    try:
        schema = from_json(json_schema_file_name)
        jsonschema.validate(file_data, schema)
        return True
    except jsonschema.ValidationError as e:
        logger.error(f'jsonschema.ValidationError: {e.message}')
        return False
    except jsonschema.SchemaError:
        return False


def process_data_information(list_data, is_get_lasted_version=False):
    list_data_version = []
    for item in list_data:
        if is_get_lasted_version:
            file_version = item['version'][0]
            current_data = {**item, **file_version}
            del current_data['version']
            list_data_version.append(current_data)
        else:
            for file_version in item['version']:
                current_data = {**item, **file_version}
                del current_data['version']
                list_data_version.append(current_data)
    return list_data_version


def float_or_none(x):
    try:
        return float(x)
    except ValueError:
        return None


def deep_diff(x, y, parent_key=None, exclude_keys=None, epsilon_keys=None):
    """
    Find the difference between 2 dictionary
    Take the deep diff of JSON-like dictionaries
    No warranties when keys, or values are None
    """
    EPSILON = 0.5
    rho = 1 - EPSILON

    if epsilon_keys is None:
        epsilon_keys = []
    if exclude_keys is None:
        exclude_keys = []

    if x == y:
        return None

    if parent_key in epsilon_keys:
        xfl, yfl = float_or_none(x), float_or_none(y)
        if xfl and yfl and xfl * yfl >= 0 and rho * xfl <= yfl and rho * yfl <= xfl:
            return None

    if type(x) != type(y) or type(x) not in [list, dict]:
        return x, y

    if type(x) == dict:
        d = {}
        for k in x.keys() ^ y.keys():
            if k in exclude_keys:
                continue
            if k in x:
                d[k] = (deepcopy(x[k]), None)
            else:
                d[k] = (None, deepcopy(y[k]))

        for k in x.keys() & y.keys():
            if k in exclude_keys:
                continue

            next_d = deep_diff(x[k], y[k], parent_key=k, exclude_keys=exclude_keys, epsilon_keys=epsilon_keys)
            if next_d is None:
                continue

            d[k] = next_d

        return d if d else None

    # assume a list:
    d = [None] * max(len(x), len(y))
    flipped = False
    if len(x) > len(y):
        flipped = True
        x, y = y, x

    for i, x_val in enumerate(x):
        if flipped:
            d[i] = deep_diff(y[i], x_val, parent_key=i, exclude_keys=exclude_keys, epsilon_keys=epsilon_keys)
        else:
            d[i] = deep_diff(x_val, y[i], parent_key=i, exclude_keys=exclude_keys, epsilon_keys=epsilon_keys)

    for i in range(len(x), len(y)):
        d[i] = (y[i], None) if flipped else (None, y[i])

    return None if all(map(lambda z: z is None, d)) else d


def check_diff_between_version(list_version_a, list_version_b, parent_key=None, exclude_keys=None, epsilon_keys=None):
    for i in range(len(list_version_a)):
        if exclude_keys is not None and 'identifier' not in exclude_keys:
            if list_version_a[i]['identifier'] != list_version_b[i]['identifier']:
                return True, 'Missing file version', list_version_b[i]
        check_diff = deep_diff(list_version_a[i], list_version_b[i], parent_key=parent_key, exclude_keys=exclude_keys, epsilon_keys=epsilon_keys)
        if check_diff:
            list_diff = list(check_diff)
            text_error = '"' + ', '.join(list_diff) + '" not match'
            return True, text_error, list_version_a[i]
        return False, '', None


def count_files_ng_ok(exported_file_versions, storage_file_versions, exclude_keys=None):
    exported_file_versions = sorted(exported_file_versions, key=lambda kv: kv['materialized_path'])
    storage_file_versions = sorted(storage_file_versions, key=lambda kv: kv['materialized_path'])
    data = {
        'ng': 0,
        'ok': 0,
    }
    list_file_ng = []
    count_files = 0
    exported_file_provider = exported_file_versions[0].get('provider')
    storage_file_provider = storage_file_versions[0].get('provider')
    for file_a in exported_file_versions:
        # following properties is not change after the Export/Restore process
        # use them to identify a file version
        version_identifier_a = file_a.get('identifier')
        materialized_path_a = file_a.get('materialized_path')
        project_id_a = file_a.get('project', {}).get('id')

        if is_add_on_storage(exported_file_provider) or is_add_on_storage(storage_file_provider):
            file_b = next((
                file for file in storage_file_versions if (
                    file.get('materialized_path') == materialized_path_a
                    and file.get('project', {}).get('id') == project_id_a
                )
            ), None)
        else:
            file_b = next((
                file for file in storage_file_versions if (
                    file.get('materialized_path') == materialized_path_a
                    and file.get('identifier') == version_identifier_a
                    and file.get('project', {}).get('id') == project_id_a
                )
            ), None)
        if file_b:
            is_diff, message, file_version = check_diff_between_version([file_a], [file_b], exclude_keys=exclude_keys)
            if not is_diff:
                data['ok'] += 1
            else:
                data['ng'] += 1
                ng_content = {
                    'project_id': project_id_a,
                    'path': materialized_path_a,
                    'version_id': version_identifier_a,
                    'size': file_a.get('size', 0),
                    'reason': message,
                }
                list_file_ng.append(ng_content)
            count_files += 1
        else:
            data['ng'] += 1
            ng_content = {
                'project_id': project_id_a,
                'path': materialized_path_a,
                'version_id': version_identifier_a,
                'size': file_a.get('size', 0),
                'reason': 'File is not exist',
            }
            list_file_ng.append(ng_content)
            count_files += 1
    data['total'] = count_files
    data['list_file_ng'] = list_file_ng
    return data


def check_for_file_existent_on_export_location(
        file_info_json, node_id, provider, file_path, location_id,
        cookies, cookie):
    # Get list file in export storage location
    file_list = get_files_in_path(node_id, provider, file_path, cookies,
                                  location_id=location_id, cookie=cookie)

    if not file_list:
        return None

    attrs = ['name', 'size']
    storage_file_list = [{attr: file.get('attributes', {}).get(attr) for attr in attrs} for file in file_list]
    storage_file_dict = {file.get('name'): file for file in storage_file_list}

    # get file data saved in file info Json
    file_versions = []
    for file in file_info_json.get('files', []):
        versions = file.get('version', [])
        file_path = file.get('materialized_path')
        project_id = file.get('project', {}).get('id')
        for version in versions:
            size = version.get('size')
            metadata = version.get('metadata')
            modified_at = version.get('modified_at')
            # get metadata.get('sha256', metadata.get('md5',
            #     metadata.get('sha512', metadata.get('sha1', metadata.get('name')))))
            file_name = metadata.get('sha256', metadata.get('md5', metadata.get('sha512', metadata.get('sha1'))))
            export_provider = file.get('provider')
            if export_provider == 'onedrivebusiness':
                # OneDrive Business: get new hash based on quickXorHash and file version modified time
                quick_xor_hash = metadata.get('quickXorHash')
                new_string_to_hash = f'{quick_xor_hash}{modified_at}'
                file_name = hashlib.sha256(new_string_to_hash.encode('utf-8')).hexdigest()
            version_name = version.get('version_name')
            version_id = version.get('identifier')
            file_versions.append({
                'project_id': project_id,
                'path': file_path,
                'name': file_name,
                'version_name': version_name,
                'version_id': version_id,
                'size': size
            })

    # compare file_list with file_versions
    list_file_ng = []
    for file in file_versions:
        if not storage_file_dict.get(file['name']):
            ng_content = {
                'path': file['path'],
                'size': file['size'],
                'version_id': file['version_id'],
                'reason': 'File does not exist on the Export Storage Location',
            }
            list_file_ng.append(ng_content)
    return list_file_ng


def check_file_metadata(data, restore_data, storage_file_info):
    destination_region = restore_data.destination
    destination_provider = destination_region.provider_name
    if not is_add_on_storage(destination_provider):
        destination_provider = 'osfstorage'
    storage_files = storage_file_info.get('files', [])
    list_file_ng = data.get('list_file_ng', [])
    for file in storage_files:
        file_materialized_path = file.get('materialized_path')
        file_project_guid = file.get('project', {}).get('id')
        file_provider = file.get('provider')
        if not is_add_on_storage(file_provider):
            file_provider = 'osfstorage'
        project = AbstractNode.load(file_project_guid)
        old_file_metadata_queryset = FileMetadata.objects.filter(project__owner=project, path=f'{file_provider}{file_materialized_path}', deleted=None)
        restored_file_metadata_queryset = FileMetadata.objects.filter(project__owner=project, path=f'{destination_provider}{file_materialized_path}', deleted=None)
        if not restored_file_metadata_queryset.exists() and old_file_metadata_queryset.exists():
            # Metadata path does not change, add to NG list
            file_is_ng = False
            for item in data.get('list_file_ng', []):
                if item.get('path') == file_materialized_path:
                    # If file already has NG, add reason
                    file_is_ng = True
                    item['reason'] += '\nFile metadata is not updated'
            if not file_is_ng:
                # If file is not NG then add new record
                data['ok'] -= 1
                data['ng'] += 1
                list_file_ng.append({
                    'path': file_materialized_path,
                    'size': file.get('size'),
                    'version_id': None,
                    'reason': 'File metadata is not updated',
                })
    data['list_file_ng'] = list_file_ng
    return data


def check_for_any_running_restore_process(destination_id):
    return ExportDataRestore.objects.filter(destination_id=destination_id).exclude(
        Q(status=ExportData.STATUS_STOPPED) | Q(status=ExportData.STATUS_COMPLETED) | Q(status=ExportData.STATUS_ERROR)).exists()


def get_file_data(node_id, provider, file_path, cookies, base_url=WATERBUTLER_URL,
                  get_file_info=False, version=None, location_id=None, **kwargs):
    if get_file_info:
        kwargs['meta'] = ''
    if version:
        kwargs['version'] = version
        kwargs['revision'] = version
    if location_id:
        kwargs['location_id'] = location_id
    file_url = waterbutler_api_url_for(node_id, provider, path=file_path, _internal=base_url == WATERBUTLER_URL, base_url=base_url, **kwargs)
    return requests.get(file_url,
                        headers={'content-type': 'application/json'},
                        cookies=cookies)


def get_files_in_path(node_id, provider, path, cookies, **kwargs):
    file_list = []
    next_token = None
    _retries = 2
    while next_token or _retries:
        # Get list file in export storage location
        if next_token:
            kwargs['next_token'] = next_token
        response = get_file_data(
            node_id, provider, path, cookies,
            **kwargs)

        # handle response
        if response.status_code == 200:
            response_body = response.json()
            new_file_list = response_body.get('data', [])
            file_list = file_list + new_file_list
            # request again if it has next_token
            next_token = response_body.get('next_token')
            _retries = 0
        else:
            _retries = max(_retries - 1, 0)
            message = (f'Failed to get info of path "{path}" on destination storage,'
                       f' create new folder on destination storage')
            if _retries:
                message = 'Try to get object list again'
            logger.warning(message)
            continue  # request again

        # stop if response new_file_list is empty
        if not new_file_list:
            break

        # stop if addon have not a max-keys (-like) option
        if provider not in ADDONS_HAS_MAX_KEYS:
            # _retries = 0
            break

    return file_list


def create_folder(node_id, provider, parent_path, folder_name, cookies, callback_log=False, base_url=WATERBUTLER_URL, **kwargs):
    kwargs.update({'callback_log': False})
    kwargs.setdefault('kind', 'folder')
    kwargs.setdefault('name', folder_name)
    upload_url = waterbutler_api_url_for(node_id, provider, path=parent_path, _internal=base_url == WATERBUTLER_URL, base_url=base_url, **kwargs)
    try:
        response = requests.put(upload_url,
                                headers={'content-type': 'application/json'},
                                cookies=cookies)
        return response.json() if response.status_code == 201 else None, response.status_code
    except Exception:
        return None, None


def upload_file(node_id, provider, file_parent_path, file_data, file_name, cookies, base_url=WATERBUTLER_URL, **kwargs):
    kwargs.update({'callback_log': False})
    upload_url = waterbutler_api_url_for(node_id, provider, path=file_parent_path, kind='file', name=file_name,
                                         _internal=base_url == WATERBUTLER_URL, base_url=base_url, **kwargs)
    try:
        response = requests.put(upload_url,
                                headers={'content-type': 'application/json'},
                                cookies=cookies,
                                data=file_data)
        return response.json() if response.status_code == 201 else None, response.status_code
    except Exception:
        return None, None


def update_existing_file(node_id, provider, file_path, file_data, cookies, base_url=WATERBUTLER_URL, **kwargs):
    kwargs.update({'callback_log': False})
    upload_url = waterbutler_api_url_for(node_id, provider, path=file_path, kind='file',
                                         _internal=base_url == WATERBUTLER_URL, base_url=base_url, **kwargs)
    try:
        response = requests.put(upload_url,
                                headers={'content-type': 'application/json'},
                                cookies=cookies,
                                data=file_data)
        return response.json() if response.status_code == 200 else None, response.status_code
    except Exception:
        return None, None


def create_folder_path(node_id, destination_region, folder_path, cookies, base_url=WATERBUTLER_URL, **kwargs):
    if not folder_path.startswith('/') and not folder_path.endswith('/'):
        # Invalid folder path, return immediately
        return

    provider = destination_region.provider_name
    is_destination_addon_storage = is_add_on_storage(provider)

    if not is_destination_addon_storage:
        _msg = 'Ignore check folder existence in institution storage bulk-mount method'
        logger.warning(_msg)
        raise Exception(_msg)

    paths = folder_path.split('/')[1:-1]
    created_path = '/'
    created_materialized_path = '/'
    for index, path in enumerate(paths):
        try:
            response = get_file_data(node_id, provider, created_path, cookies, base_url, get_file_info=False, **kwargs)
            if response.status_code != 200:
                raise Exception('Cannot get folder info')
            response_body = response.json()
            new_path = f'{created_materialized_path}{path}/'
            existing_path_info = next((item for item in response_body['data'] if
                                       item['attributes']['materialized'] == new_path),
                                      None)
            if existing_path_info is None:
                raise Exception('Folder not found')

            created_path = existing_path_info['attributes']['path']
            created_materialized_path = existing_path_info['attributes']['materialized']
        except Exception:
            # If currently at folder, create folder
            response_body, status_code = create_folder(
                node_id, provider, created_path, path, cookies,
                callback_log=True, base_url=base_url, **kwargs)
            if response_body is not None:
                created_path = response_body['data']['attributes']['path']
                created_materialized_path = response_body['data']['attributes']['materialized']
            else:
                return


def upload_file_path(node_id, provider, file_path, file_data, cookies, base_url=WATERBUTLER_URL, **kwargs):
    if not file_path.startswith('/') or file_path.endswith('/'):
        # Invalid file path, return immediately
        return {}

    paths = file_path.split('/')[1:]
    created_path = '/'
    created_materialized_path = '/'
    for index, path in enumerate(paths):
        try:
            # Try to get path information
            response = get_file_data(node_id, provider, created_path,
                                     cookies, base_url, get_file_info=True, **kwargs)
            if response.status_code != 200:
                raise Exception('Cannot get folder info')
            response_body = response.json()

            if index == len(paths) - 1:
                new_path = f'{created_materialized_path}{path}'
            else:
                new_path = f'{created_materialized_path}{path}/'

            existing_path_info = next((item for item in response_body['data'] if
                                       item['attributes']['materialized'] == new_path),
                                      None)
            if existing_path_info is None:
                raise Exception('Folder not found')

            created_path = existing_path_info['attributes']['path']
            created_materialized_path = existing_path_info['attributes']['materialized']
            if index == len(paths) - 1:
                # If currently at file name, update file
                update_response_body, update_status_code = update_existing_file(node_id, provider,
                                                                                created_path,
                                                                                file_data, cookies,
                                                                                base_url, **kwargs)
                return update_response_body
        except Exception:
            if index == len(paths) - 1:
                # If currently at file name, upload file
                response_body, status_code = upload_file(node_id, provider, created_path, file_data, path,
                                                         cookies, base_url, **kwargs)
                return response_body
            else:
                # If currently at folder, create folder
                response_body, status_code = create_folder(
                    node_id, provider, created_path, path, cookies,
                    callback_log=True, base_url=base_url, **kwargs)
                if response_body is not None:
                    created_path = response_body['data']['attributes']['path']
                    created_materialized_path = response_body['data']['attributes']['materialized']
                else:
                    return {}


def copy_file_to_other_storage(export_data, destination_node_id, destination_provider, location_file_path, destination_parent_path, file_name, cookies, base_url=WATERBUTLER_URL, **kwargs):
    location_node_id = export_data.EXPORT_DATA_FAKE_NODE_ID
    location_provider = export_data.location.provider_name

    copy_file_url = waterbutler_api_url_for(
        location_node_id, location_provider, path=location_file_path,
        _internal=True, base_url=base_url, callback_log=False,
        location_id=export_data.location.id, **kwargs)

    request_body = {
        'action': 'copy',
        'path': destination_parent_path,
        'conflict': 'replace',
        'rename': file_name,
        'resource': destination_node_id,
        'provider': destination_provider,
        'synchronous': True,
    }

    try:
        response = requests.post(copy_file_url,
                                 headers={'content-type': 'application/json'},
                                 cookies=cookies,
                                 json=request_body,
                                 timeout=EACH_FILE_EXPORT_RESTORE_TIME_OUT)
        return response.json() if response.status_code in [200, 201] else None
    except (requests.ConnectionError, requests.Timeout, requests.ReadTimeout) as e:
        logger.error(f'Timeout exception occurs: {e}')
        return None
    except Exception as e:
        logger.error(f'Exception: {e}')
        return None


def copy_file_from_location_to_destination(
        export_data, destination_node_id, destination_provider, location_file_path, destination_file_path, cookies,
        base_url=WATERBUTLER_URL, **kwargs):
    if not destination_file_path.startswith('/') or destination_file_path.endswith('/'):
        # Invalid file path, return immediately
        return None

    folder_paths = destination_file_path.split('/')[1:-1]
    file_name = destination_file_path.split('/')[-1]
    created_folder_path = '/'
    created_folder_materialized_path = '/'

    # Get file's parent folder path for copy API
    for path in folder_paths:
        try:
            # Try to get path information
            file_list = get_files_in_path(destination_node_id, destination_provider, created_folder_path, cookies,
                                          base_url=base_url,
                                          get_file_info=True,
                                          **kwargs)
            if not file_list:
                raise Exception('Empty folder')

            new_folder_path = f'{created_folder_materialized_path}{path}/'
            existing_path_info = next((item for item in file_list if
                                       item['attributes']['materialized'] == new_folder_path),
                                      None)

            if existing_path_info is None:
                message = (f'Path "{new_folder_path}" is not found on destination storage,'
                           f' create new folder on destination storage')
                logger.warning(message)
                raise Exception(message)

            created_folder_path = existing_path_info['attributes']['path']
            created_folder_materialized_path = existing_path_info['attributes']['materialized']
        except Exception:
            # If currently at folder, create folder
            response_body, status_code = create_folder(
                destination_node_id, destination_provider, created_folder_path, path, cookies,
                callback_log=True, base_url=base_url, **kwargs)
            if response_body is not None:
                created_folder_path = response_body['data']['attributes']['path']
                created_folder_materialized_path = response_body['data']['attributes']['materialized']
            else:
                return None

    # Call API to copy file from location storage to destination storage
    copy_response_body = copy_file_to_other_storage(export_data, destination_node_id, destination_provider, location_file_path,
                                                    created_folder_path, file_name, cookies, **kwargs)
    return copy_response_body


def prepare_file_node_for_add_on_storage(node_id, provider, file_path, **kwargs):
    """ Add new file node record for add-on storage """
    if not is_add_on_storage(provider):
        # Bulk-mount storage already created file node from other functions, do nothing here
        return

    with transaction.atomic():
        node = AbstractNode.load(node_id)
        if node.type == 'osf.node':
            # Only get or create file nodes that belongs to projects
            file_node = BaseFileNode.resolve_class(provider, BaseFileNode.FILE).get_or_create(node, file_path)
            extras = {'cookie': kwargs.get('cookie')}
            file_node.touch(
                auth_header=None,
                **extras,
            )
        # signals.file_updated.send(target=node, user=user, event_type=NodeLog.FILE_COPIED, payload=payload)


def is_add_on_storage(provider):
    if not provider:
        return None

    # If provider is institutional bulk-mount storages then return False
    if provider in INSTITUTIONAL_STORAGE_BULK_MOUNT_METHOD:
        return False

    # If provider is institutional addon storages then return True
    if provider in INSTITUTIONAL_STORAGE_ADD_ON_METHOD:
        return True

    # Default value for unknown provider
    return None


def update_file_metadata(project_guid, source_provider, destination_provider, file_path):
    """ Update restored file path of addons_metadata_filemetadata """
    project = AbstractNode.load(project_guid)
    if not project:
        return

    old_metadata_path = f'{source_provider}{file_path}'
    new_metadata_path = f'{destination_provider}{file_path}'
    file_metadata_queryset = FileMetadata.objects.filter(project__owner=project, path=old_metadata_path, deleted=None)
    if file_metadata_queryset.exists():
        file_metadata = file_metadata_queryset.first()
        file_metadata.path = new_metadata_path
        file_metadata.save()


def update_all_folders_metadata(institution, destination_provider):
    """ Update folder path of addons_metadata_filemetadata """
    if not institution or is_add_on_storage(destination_provider) is None:
        # If input is invalid then do nothing
        return

    with transaction.atomic():
        institution_users = institution.osfuser_set.all()
        project_queryset = AbstractNode.objects.filter(type='osf.node', is_deleted=False, creator__in=institution_users)
        file_metadata_list = FileMetadata.objects.filter(folder=True, project__owner__in=project_queryset, deleted=None)
        for file_metadata in file_metadata_list:
            path = file_metadata.path
            path_parts = path.split('/')
            if len(path_parts) > 1:
                path_parts[0] = destination_provider
                file_metadata.path = '/'.join(path_parts)
                file_metadata.save()
