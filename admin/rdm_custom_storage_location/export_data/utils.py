# -*- coding: utf-8 -*-
import inspect  # noqa
import json  # noqa
import logging  # noqa
import re
from copy import deepcopy

import jsonschema
import requests
from django.db.models import Q
from rest_framework import status as http_status

from addons.base.institutions_utils import KEYNAME_BASE_FOLDER
from addons.dropboxbusiness import utils as dropboxbusiness_utils
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
)
from website.settings import WATERBUTLER_URL, INSTITUTIONAL_STORAGE_ADD_ON_METHOD, INSTITUTIONAL_STORAGE_BULK_MOUNT_METHOD
from website.util import inspect_info  # noqa

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


def process_data_information(list_data):
    list_data_version = []
    for item in list_data:
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
    for file_a in exported_file_versions:
        version_identifier_a = file_a['identifier']
        materialized_path_a = file_a.get('materialized_path')

        file_b = next((
            file for file in storage_file_versions
            if file.get('materialized_path') == materialized_path_a and file.get('identifier') == version_identifier_a
        ), None)
        if file_b:
            is_diff, message, file_version = check_diff_between_version([file_a], [file_b], exclude_keys=exclude_keys)
            if not is_diff:
                data['ok'] += 1
            else:
                data['ng'] += 1
                ng_content = {
                    'path': materialized_path_a,
                    'size': file_a['size'],
                    'version_id': file_a['identifier'],
                    'reason': message,
                }
                list_file_ng.append(ng_content)
            count_files += 1
        else:
            data['ng'] += 1
            ng_content = {
                'path': materialized_path_a,
                'size': file_a['size'],
                'version_id': file_a.get('identifier', 0),
                'reason': 'File is not exist',
            }
            list_file_ng.append(ng_content)
            count_files += 1
    data['total'] = count_files
    data['list_file_ng'] = list_file_ng if len(list_file_ng) <= 10 else list_file_ng[:10]
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


def create_folder(node_id, provider, parent_path, folder_name, cookies, callback_log=False, base_url=WATERBUTLER_URL, **kwargs):
    kwargs.setdefault('kind', 'folder')
    kwargs.setdefault('callback_log', callback_log)
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


def create_folder_path(node_id, provider, folder_path, cookies, base_url=WATERBUTLER_URL, **kwargs):
    if not folder_path.startswith('/') and not folder_path.endswith('/'):
        # Invalid folder path, return immediately
        return
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


def move_file(node_id, provider, source_file_path, destination_file_path, cookies, callback_log=False,
              base_url=WATERBUTLER_URL, is_addon_storage=True, **kwargs):
    move_old_data_url = waterbutler_api_url_for(
        node_id, provider, path=source_file_path, _internal=base_url == WATERBUTLER_URL,
        base_url=base_url, callback_log=callback_log, **kwargs)
    if is_addon_storage:
        # Add on storage: move whole source path to root and rename to destination path
        destination_file_path = destination_file_path[1:] if destination_file_path.startswith('/') \
            else destination_file_path
        request_body = {
            'action': 'move',
            'path': '/',
            'rename': destination_file_path,
        }
    else:
        # Bulk mount storage: move source folder to destination folder
        request_body = {
            'action': 'move',
            'path': destination_file_path,
        }
    return requests.post(move_old_data_url,
                         headers={'content-type': 'application/json'},
                         cookies=cookies,
                         json=request_body)


def move_addon_folder_to_backup(
        node_id, provider, process_start, cookies, callback_log=False,
        base_url=WATERBUTLER_URL, check_abort_task=None, **kwargs):
    path_list, root_child_folders = get_all_file_paths_in_addon_storage(
        node_id, provider, '/', cookies, base_url, exclude_path_regex=ANY_BACKUP_FOLDER_REGEX, **kwargs)
    if len(path_list) == 0:
        return {}

    # Move file
    has_error = False
    error_message = ''
    for path in path_list:
        if callable(check_abort_task):
            check_abort_task()
        try:
            paths = path.split('/')
            paths.insert(1, f'backup_{process_start}')
            new_path = '/'.join(paths)
            response = move_file(node_id, provider, path, new_path, cookies,
                                 callback_log, base_url, is_addon_storage=True, **kwargs)
            if response.status_code != 200 and response.status_code != 201 and response.status_code != 202:
                logger.error(f'Response return error: {response.content}')
                has_error = True
                error_message = f'{response.status_code} - {response.content}'
                break
        except Exception as e:
            if callable(check_abort_task):
                check_abort_task()
            logger.error(f'Exception: {e}')
            has_error = True
            error_message = repr(e)
            break

    if has_error:
        return {'error': error_message}

    # S3: Clean root folders after moving
    delete_paths(node_id, provider, root_child_folders,
                 cookies, callback_log, base_url, **kwargs)
    return {}


def move_addon_folder_from_backup(node_id, provider, process_start, cookies, callback_log=False, base_url=WATERBUTLER_URL, **kwargs):
    path_list, root_child_folders = get_all_file_paths_in_addon_storage(
        node_id, provider, '/', cookies, base_url, include_path_regex=f'^\\/backup_{process_start}\\/.*$', **kwargs)
    if len(path_list) == 0:
        return {}

    # Move files and folders from backup to root
    has_error = False
    error_message = ''
    for path in path_list:
        try:
            paths = path.split('/')
            if paths[1] == f'backup_{process_start}':
                del paths[1]
            else:
                continue
            new_path = '/'.join(paths)
            response = move_file(node_id, provider, path, new_path,
                                 cookies, callback_log, base_url, is_addon_storage=True, **kwargs)
            if response.status_code != 200 and response.status_code != 201 and response.status_code != 202:
                logger.error(f'Response return error: {response.content}')
                has_error = True
                error_message = f'{response.status_code} - {response.content}'
                break
        except Exception as e:
            logger.error(f'Exception: {e}')
            has_error = True
            error_message = repr(e)
            break

    if has_error:
        return {'error': error_message}

    # S3: Clean backup folders after moving
    delete_paths(node_id, provider, root_child_folders,
                 cookies, callback_log, base_url, **kwargs)
    return {}


def get_all_file_paths_in_addon_storage(node_id, provider, file_path, cookies, base_url=WATERBUTLER_URL,
                                        include_path_regex='', exclude_path_regex='', **kwargs):
    try:
        response = get_file_data(node_id, provider, file_path, cookies, base_url=base_url, get_file_info=True, **kwargs)
        if response.status_code != 200:
            return [], []
        response_body = response.json()
        data = response_body.get('data')
        if len(data) != 0:
            list_file_path = []
            root_child_folders = []
            for item in data:
                path = item.get('attributes', {}).get('path')
                materialized_path = item.get('attributes', {}).get('materialized')
                kind = item.get('attributes', {}).get('kind')

                try:
                    if isinstance(include_path_regex, str) and len(include_path_regex) != 0:
                        pattern = re.compile(include_path_regex)
                        if not pattern.match(materialized_path):
                            continue
                    if isinstance(exclude_path_regex, str) and len(exclude_path_regex) != 0:
                        pattern = re.compile(exclude_path_regex)
                        if pattern.match(materialized_path):
                            continue
                except Exception as e:
                    logger.error(f'Exception: {e}')
                    continue

                if kind == 'file':
                    list_file_path.append(path)
                elif kind == 'folder':
                    if file_path == '/':
                        # S3: Add to list need to delete
                        root_child_folders.append(path)
                    # Call this function again
                    sub_file_paths, _ = get_all_file_paths_in_addon_storage(node_id, provider, path, cookies, base_url, **kwargs)
                    list_file_path.extend(sub_file_paths)

            return list_file_path, root_child_folders
        else:
            return [file_path], []
    except Exception:
        return [], []


def move_bulk_mount_folder_to_backup(
        node_id, provider, process_start, cookies, callback_log=False,
        base_url=WATERBUTLER_URL, check_abort_task=None, **kwargs):
    path_list, _ = get_all_child_paths_in_bulk_mount_storage(
        node_id, provider, '/', cookies, base_url, exclude_path_regex=ANY_BACKUP_FOLDER_REGEX, **kwargs)
    if len(path_list) == 0:
        return {}

    # Move file
    has_error = False
    error_message = ''
    new_materialized_path = f'/backup_{process_start}/'

    # OSF storage: create new backup folder
    try:
        if callable(check_abort_task):
            check_abort_task()
        response_body, status_code = create_folder(node_id, provider, '/', new_materialized_path[1:],
                                                   cookies, callback_log, base_url, **kwargs)
        if status_code != 201:
            return {'error': 'Cannot create backup folder'}
        new_path = response_body['data']['attributes']['path']
    except Exception as e:
        logger.error(f'Exception: {e}')
        return {'error': repr(e)}

    # Move all root child files and folders to backup folder
    for path, materialized_path in path_list:
        if callable(check_abort_task):
            check_abort_task()
        try:
            response = move_file(node_id, provider, path, new_path,
                                 cookies, callback_log, base_url, is_addon_storage=False, **kwargs)
            if response.status_code != 200 and response.status_code != 201 and response.status_code != 202:
                logger.error(f'Response return error: {response.content}')
                # Rollback
                has_error = True
                error_message = f'{response.status_code} - {response.content}'
                break
        except Exception as e:
            logger.error(f'Exception: {e}')
            has_error = True
            error_message = repr(e)
            break

    if has_error:
        return {'error': error_message}
    return {}


def move_bulk_mount_folder_from_backup(node_id, provider, process_start, cookies, callback_log=False, base_url=WATERBUTLER_URL, **kwargs):
    path_list, backup_path = get_all_child_paths_in_bulk_mount_storage(
        node_id, provider, f'/backup_{process_start}/',
        cookies, base_url, get_path_from=f'/backup_{process_start}/', **kwargs)
    if len(path_list) == 0:
        return {}

    # Move files and folders from backup to root
    has_error = False
    error_message = ''
    root_path = '/'
    for path, materialized_path in path_list:
        try:
            response = move_file(node_id, provider, path, root_path,
                                 cookies, callback_log, base_url, is_addon_storage=False, **kwargs)
            if response.status_code != 200 and response.status_code != 201 and response.status_code != 202:
                logger.error(f'Response return error: {response.content}')
                has_error = True
                error_message = f'{response.status_code} - {response.content}'
                break
        except Exception as e:
            logger.error(f'Exception: {e}')
            has_error = True
            error_message = repr(e)
            break

    if has_error:
        return {'error': error_message}

    # OSF storage: Delete backup folder after moving
    delete_paths(node_id, provider, [backup_path], cookies, callback_log, base_url, **kwargs)
    return {}


def get_all_child_paths_in_bulk_mount_storage(
        node_id, provider, file_materialized_path, cookies,
        base_url=WATERBUTLER_URL, exclude_path_regex='', get_path_from='', **kwargs):
    list_file_path = []
    path_from_args = None
    try:
        if not file_materialized_path.startswith('/') or not file_materialized_path.endswith('/'):
            return list_file_path, path_from_args
        paths = file_materialized_path.split('/')[1:]
        if len(paths) > 0:
            current_path = '/'
            current_materialized_path = '/'
            for index, path in enumerate(paths):
                response = get_file_data(node_id, provider, current_path, cookies, base_url=base_url, get_file_info=True, **kwargs)
                if response.status_code != 200:
                    return [], None
                response_body = response.json()
                data = response_body.get('data', [])
                if index == len(paths) - 1:
                    for item in data:
                        path = item.get('attributes', {}).get('path')
                        materialized_path = item.get('attributes', {}).get('materialized')
                        try:
                            if isinstance(exclude_path_regex, str) and len(exclude_path_regex) != 0:
                                pattern = re.compile(exclude_path_regex)
                                if pattern.match(materialized_path):
                                    continue
                        except Exception as e:
                            logger.error(f'Exception: {e}')
                            continue
                        list_file_path.append((path, materialized_path))
                else:
                    current_materialized_path = f'{current_materialized_path}{path}/'
                    current_path_info = next((item for item in data if item.get('attributes', {}).get('materialized') ==
                                              current_materialized_path), None)
                    if current_path_info is None:
                        break

                    current_path = current_path_info['attributes']['path']
                    if current_path_info['attributes']['materialized'] == get_path_from:
                        path_from_args = current_path
        return list_file_path, path_from_args
    except Exception:
        return list_file_path, path_from_args


def delete_paths(node_id, provider, paths,
                 cookies, callback_log=False, base_url=WATERBUTLER_URL, **kwargs):
    for path in paths:
        try:
            delete_file(node_id, provider, path,
                        cookies, callback_log, base_url, **kwargs)
        except Exception as e:
            logger.error(f'Exception: {e}')


def delete_file(node_id, provider, file_path, cookies, callback_log=False, base_url=WATERBUTLER_URL, **kwargs):
    destination_storage_backup_meta_api = waterbutler_api_url_for(
        node_id, provider, path=file_path,
        _internal=base_url == WATERBUTLER_URL, base_url=base_url,
        callback_log=callback_log, **kwargs)
    return requests.delete(destination_storage_backup_meta_api,
                           headers={'content-type': 'application/json'},
                           cookies=cookies)


def delete_all_files_except_backup(node_id, provider, cookies, callback_log=False, base_url=WATERBUTLER_URL, **kwargs):
    # In add-on institutional storage: Delete files, except the backup folder.
    list_not_backup_paths = []
    try:
        response = get_file_data(node_id, provider, '/', cookies, base_url=base_url, get_file_info=True, **kwargs)
        if response.status_code != 200:
            raise Exception(f'Cannot get file info list.')
        response_body = response.json()
        data = response_body.get('data')
        if len(data) != 0:
            for item in data:
                path = item.get('attributes', {}).get('path')
                materialized_path = item.get('attributes', {}).get('materialized')
                kind = item.get('attributes', {}).get('kind')

                try:
                    pattern = re.compile(ANY_BACKUP_FOLDER_REGEX)
                    if pattern.match(materialized_path):
                        continue
                except Exception as e:
                    logger.error(f'Exception: {e}')

                if kind == 'file' or kind == 'folder':
                    list_not_backup_paths.append(path)
    except (requests.ConnectionError, requests.Timeout) as e:
        logger.error(f'Connection error: {e}')
        raise e

    # Delete all paths
    for path in list_not_backup_paths:
        try:
            delete_file(node_id, provider, path, cookies, callback_log, base_url, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as e:
            logger.error(f'Connection error: {e}')
            raise e


def is_add_on_storage(provider):
    if not provider:
        return None

    # If provider is institutional addon storages then return True
    if provider in INSTITUTIONAL_STORAGE_ADD_ON_METHOD:
        return True

    # If provider is institutional bulk-mount storages then return False
    if provider in INSTITUTIONAL_STORAGE_BULK_MOUNT_METHOD:
        return False

    # Default value for unknown provider
    return None
