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
    Institution,
    FileVersion,
    BaseFileVersionsThrough,
    BaseFileNode,
    AbstractNode,
    OSFUser,
    RdmFileTimestamptokenVerifyResult,
    Guid,
    ExternalAccount,
)
from website.settings import WATERBUTLER_URL
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
    'validate_export_data',
    'write_json_file',
    'check_diff_between_version',
    'count_files_ng_ok',
]


def write_json_file(json_data, output_file):
    """Write json data to a file

    Args:
        json_data: data in json or dictionary
        output_file: the full path of output file

    Raises:
        Exception - Exception when writing the file
    """
    with open(output_file, "w", encoding='utf-8') as write_file:
        try:
            json.dump(json_data, write_file, ensure_ascii=False, indent=2, sort_keys=False)
        except Exception as exc:
            raise Exception(f"Cannot write json file. Exception: {str(exc)}")


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
        return ({
                    'message': u'Invalid Institution ID.: {}'.format(institution.id)
                }, http_status.HTTP_400_BAD_REQUEST)

    f_option, m_option = fm
    f_token = dropboxbusiness_utils.addon_option_to_token(f_option)
    m_token = dropboxbusiness_utils.addon_option_to_token(m_option)
    if f_token is None or m_token is None:
        return ({
                    'message': 'No tokens.'
                }, http_status.HTTP_400_BAD_REQUEST)
    try:
        # use two tokens and connect
        dropboxbusiness_utils.TeamInfo(f_token, m_token, connecttest=True)
        return ({
                    'message': 'Credentials are valid',
                }, http_status.HTTP_200_OK)
    except Exception:
        return ({
                    'message': 'Invalid tokens.'
                }, http_status.HTTP_400_BAD_REQUEST)


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

    update_storage_location(institution_guid, storage_name, wb_credentials, wb_settings)

    return ({
                'message': 'Saved credentials successfully!!'
            }, http_status.HTTP_200_OK)


def save_dropboxbusiness_credentials(institution, storage_name, provider_name):
    test_connection_result = test_dropboxbusiness_connection(institution)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    fm = dropboxbusiness_utils.get_two_addon_options(institution.id)
    if fm is None:
        institution = Institution.objects.get(id=institution.id)
        logger.info(u'Institution({}) has no valid oauth keys.'.format(institution.name))
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
        # team_name = team_info.name
        # fmt = six.u(dropboxbusiness_settings.TEAM_FOLDER_NAME_FORMAT)
        # team_folder_name = fmt.format(title='Location', guid=institution.guid)
        # fmt = six.u(dropboxbusiness_settings.GROUP_NAME_FORMAT)
        # group_name = fmt.format(title='Location', guid=institution.guid)
        team_folder_id = list(team_info.team_folders.keys())[0]
        # member_emails = team_info.dbmid_to_email.values()
        # team_folder_id, group_id = dropboxbusiness_utils.create_team_folder(
        #     f_token, m_token, admin_dbmid, team_folder_name, group_name, member_emails, admin_group, team_name)
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

    return ({
                'message': 'Dropbox Business was set successfully!!'
            }, http_status.HTTP_200_OK)


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

    return ({
                'message': 'Saved credentials successfully!!'
            }, http_status.HTTP_200_OK)


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


def get_provider_and_base_url_from_destination_storage(destination_id):
    destination_region = Region.objects.filter(id=destination_id)
    destination_base_url, destination_settings = destination_region.values_list("waterbutler_url",
                                                                                "waterbutler_settings")[0]
    destination_provider = destination_settings.get("storage", {}).get("provider")
    return destination_provider, destination_base_url


def is_add_on_storage(waterbutler_settings):
    storage = waterbutler_settings.get("storage")
    if not storage:
        return None
    provider = storage.get("provider")
    if not provider:
        return None

    addon_only_providers = [
        "nextcloudinstitutions",
        "dropboxbusiness",
        "s3compatinstitutions"
    ]
    bulk_mount_only_providers = [
        "box",
        "nextcloud",
        "osfstorage",
        "swift"
    ]

    # If provider is institutional addon only providers then return True
    if provider in addon_only_providers:
        return True

    # If provider is institutional bulk-mount only providers then return False
    if provider in bulk_mount_only_providers:
        return False

    # If provider is S3 or S3 compatible then do additional check for folder setting
    if provider == "s3" or provider == "s3compat":
        folder = storage.get("folder")
        if not folder:
            return None
        try:
            if isinstance(folder, str) or not "encrypt_uploads" in folder:
                # If folder does not have "encrypt_uploads" then it is add-on storage
                return True
            # If folder has "encrypt_uploads" key and it is set to True then it is bulk-mounted storage
            return False
        except ValueError as e:
            # Cannot parse folder as json, storage is add-on storage
            return True

    # Default value for unknown provider
    return None


def check_storage_type(storage_id):
    region = Region.objects.filter(id=storage_id)
    settings = region.values_list("waterbutler_settings", flat=True)[0]
    return is_add_on_storage(settings)


def check_any_running_restore_process(destination_id):
    return ExportDataRestore.objects.filter(destination_id=destination_id).exclude(
        Q(status=ExportData.STATUS_STOPPED) | Q(status=ExportData.STATUS_COMPLETED)).exists()


def validate_file_json(file_data, json_schema_file_name):
    try:
        schema = from_json(json_schema_file_name)
        jsonschema.validate(file_data, schema)
        return True
    except jsonschema.ValidationError as e:
        logger.error(f"{e.message}")
        return False
    except jsonschema.SchemaError:
        return False


def get_file_data(node_id, provider, file_path, cookies, internal=True, base_url=WATERBUTLER_URL,
                  get_file_info=False, version=None, location_id=None):
    kwargs = {}
    if get_file_info:
        kwargs["meta"] = ""
    if version:
        kwargs["version"] = version
    if location_id:
        kwargs["location_id"] = location_id
    file_url = waterbutler_api_url_for(node_id, provider, path=file_path, _internal=internal, base_url=base_url, **kwargs)
    return requests.get(file_url,
                        headers={'content-type': 'application/json'},
                        cookies=cookies)


def create_folder(node_id, provider, parent_path, folder_name, cookies, internal=True, base_url=WATERBUTLER_URL):
    upload_url = waterbutler_api_url_for(node_id, provider, path=parent_path, kind="folder", name=folder_name,
                                         _internal=internal, base_url=base_url)
    try:
        response = requests.put(upload_url,
                                headers={'content-type': 'application/json'},
                                cookies=cookies)
        return response.json() if response.status_code == 201 else None, response.status_code
    except Exception as e:
        return None, None


def upload_file(node_id, provider, file_parent_path, file_data, file_name, cookies,
                internal=True, base_url=WATERBUTLER_URL):
    upload_url = waterbutler_api_url_for(node_id, provider, path=file_parent_path, kind="file", name=file_name,
                                         _internal=internal, base_url=base_url)
    try:
        response = requests.put(upload_url,
                                headers={'content-type': 'application/json'},
                                cookies=cookies,
                                data=file_data)
        return response.json() if response.status_code == 201 else None, response.status_code
    except Exception as e:
        return None, None


def update_existing_file(node_id, provider, file_parent_path, file_data, file_name, cookies,
                         internal=True, base_url=WATERBUTLER_URL):
    upload_url = waterbutler_api_url_for(node_id, provider, path=f"{file_parent_path}{file_name}", kind="file",
                                         _internal=internal, base_url=base_url)
    try:
        response = requests.put(upload_url,
                                headers={'content-type': 'application/json'},
                                cookies=cookies,
                                data=file_data)
        return response.json() if response.status_code == 200 else None, response.status_code
    except Exception as e:
        return None, None


def upload_file_path(node_id, provider, file_path, file_data, cookies, internal=True, base_url=WATERBUTLER_URL):
    if not file_path.startswith("/") or file_path.endswith("/"):
        # Invalid file path, return immediately
        return None

    paths = file_path.split("/")[1:]
    created_folder_path = "/"
    for index, path in enumerate(paths):
        if index < len(paths) - 1:
            # Subpath is folder, try to create new folder
            response_body, status_code = create_folder(node_id, provider, created_folder_path, path, cookies, internal,
                                                       base_url)
            if response_body is not None:
                created_folder_path = response_body["data"]["attributes"]["path"]
            elif status_code == 409:
                # Folder already exists, get folder possibly encrypted path
                try:
                    response = get_file_data(node_id, provider, created_folder_path,
                                             cookies, internal, base_url, get_file_info=True)
                    if response.status_code != 200:
                        return None
                    response_body = response.json()
                    existing_path_info = next((item for item in response_body["data"] if
                                               item["attributes"]["materialized"] == f"{created_folder_path}{path}/"),
                                              None)
                    if existing_path_info is None:
                        return None
                    created_folder_path = existing_path_info["attributes"]["path"]
                except Exception as e:
                    return None
            else:
                return None
        else:
            # Subpath is file, try to create new file
            response_body, status_code = upload_file(node_id, provider, created_folder_path, file_data, path, cookies,
                                                     internal, base_url)
            if status_code == 409:
                update_response_body, update_status_code = update_existing_file(node_id, provider, created_folder_path,
                                                                                file_data, path, cookies,
                                                                                internal, base_url)
                return update_response_body
            return response_body


def move_file(node_id, provider, source_file_path, destination_file_path, cookies, internal=True,
              base_url=WATERBUTLER_URL, is_addon_storage=True):
    move_old_data_url = waterbutler_api_url_for(node_id, provider, path=source_file_path, _internal=internal,
                                                base_url=base_url)
    if is_addon_storage:
        destination_file_path = destination_file_path[1:] if destination_file_path.startswith("/")\
            else destination_file_path
        request_body = {
            "action": "move",
            "path": "/",
            "rename": destination_file_path,
        }
    else:
        request_body = {
            "action": "move",
            "path": destination_file_path,
        }
    return requests.post(move_old_data_url,
                         headers={'content-type': 'application/json'},
                         cookies=cookies,
                         json=request_body)


def move_addon_folder_to_backup(node_id, provider, process_start, cookies, internal=True, base_url=WATERBUTLER_URL):
    path_list, root_child_folders = get_all_file_paths_in_addon_storage(node_id, provider, "/", cookies, internal,
                                                                        base_url, exclude_path_regex="^\\/backup_\\d{8}T\\d{6}\\/.*$")
    if len(path_list) == 0:
        return {}

    # Move file
    moved_paths = []
    created_folder_paths = set()
    has_error = False
    error_message = ""
    for path in path_list:
        try:
            paths = path.split("/")
            paths.insert(1, f"backup_{process_start}")
            new_path = "/".join(paths)
            response = move_file(node_id, provider, path, new_path, cookies, internal, base_url, is_addon_storage=True)
            if response.status_code != 200 and response.status_code != 201 and response.status_code != 202:
                logger.error(f"Response return error: {response.content}")
                has_error = True
                error_message = f"{response.status_code} - {response.content}"
                break
            moved_paths.append((path, new_path))
            if len(paths) > 2:
                created_folder_paths.add(f"/{paths[1]}/")
        except Exception as e:
            logger.error(f"Exception: {e}")
            has_error = True
            error_message = repr(e)
            break

    if has_error:
        # Rollback
        rollback_folder_movement(node_id, provider, moved_paths, created_folder_paths, cookies, internal, base_url)
        return {"error": error_message}

    # S3: Clean root folders after moving
    delete_paths(node_id, provider, root_child_folders, cookies, internal, base_url)
    return {}


def move_addon_folder_from_backup(node_id, provider, process_start, cookies, internal=True, base_url=WATERBUTLER_URL):
    path_list, root_child_folders = get_all_file_paths_in_addon_storage(node_id, provider, "/", cookies, internal,
                                                                        base_url, include_path_regex=f"^\\/backup_{process_start}\\/.*$")
    if len(path_list) == 0:
        return {}

    # Move files and folders from backup to root
    moved_paths = []
    created_folder_paths = set()
    has_error = False
    error_message = ""
    for path in path_list:
        try:
            paths = path.split("/")
            if paths[1] == f"backup_{process_start}":
                del paths[1]
            else:
                continue
            new_path = "/".join(paths)
            response = move_file(node_id, provider, path, new_path, cookies, internal, base_url, is_addon_storage=True)
            if response.status_code != 200 and response.status_code != 201 and response.status_code != 202:
                logger.error(f"Response return error: {response.content}")
                has_error = True
                error_message = f"{response.status_code} - {response.content}"
                break
            moved_paths.append((path, new_path))
            if len(paths) > 2:
                created_folder_paths.add(f"/{paths[1]}/")
        except Exception as e:
            logger.error(f"Exception: {e}")
            has_error = True
            error_message = repr(e)
            break

    if has_error:
        # Rollback
        rollback_folder_movement(node_id, provider, moved_paths, created_folder_paths, cookies, internal, base_url)
        return {"error": error_message}

    # S3: Clean backup folders after moving
    delete_paths(node_id, provider, root_child_folders, cookies, internal, base_url)
    return {}


def get_all_file_paths_in_addon_storage(node_id, provider, file_path, cookies, internal=True, base_url=WATERBUTLER_URL,
                                        include_path_regex="", exclude_path_regex=""):
    try:
        response = get_file_data(node_id, provider, file_path, cookies, internal=internal,
                                 base_url=base_url, get_file_info=True)
        if response.status_code != 200:
            return []
        response_body = response.json()
        data = response_body.get("data")
        if len(data) != 0:
            list_file_path = []
            root_child_folders = []
            for item in data:
                path = item.get("attributes", {}).get("path")
                materialized_path = item.get("attributes", {}).get("materialized")
                kind = item.get("attributes", {}).get("kind")

                try:
                    if isinstance(include_path_regex, str) and len(include_path_regex) != 0:
                        pattern = re.compile(include_path_regex)
                        if not pattern.match(materialized_path):
                            continue
                    if isinstance(exclude_path_regex, str) and len(exclude_path_regex) != 0:
                        pattern = re.compile(exclude_path_regex)
                        if pattern.match(materialized_path):
                            continue
                except Exception:
                    continue

                if kind == "file":
                    list_file_path.append(path)
                elif kind == "folder":
                    if file_path == "/":
                        # S3: Add to list need to delete
                        root_child_folders.append(path)
                    # Call this function again
                    sub_file_paths, _ = get_all_file_paths_in_addon_storage(node_id, provider, path, cookies, internal,
                                                                            base_url)
                    list_file_path.extend(sub_file_paths)

            return list_file_path, root_child_folders
        else:
            return [file_path], []
    except Exception:
        return [], []


def move_bulk_mount_folder_to_backup(node_id, provider, process_start, cookies, internal=True, base_url=WATERBUTLER_URL):
    path_list, _ = get_all_child_paths_in_bulk_mount_storage(node_id, provider, "/", cookies, internal, base_url,
                                                             exclude_path_regex="^\\/backup_\\d{8}T\\d{6}\\/.*$")
    if len(path_list) == 0:
        return {}

    # Move file
    moved_paths = []
    has_error = False
    error_message = ""
    new_materialized_path = f"/backup_{process_start}/"

    # OSF storage: create new backup folder
    try:
        response_body, status_code = create_folder(node_id, provider, "/", new_materialized_path[1:],
                                                   cookies, internal, base_url)
        if status_code != 201:
            return {"error": "Cannot create backup folder"}
        new_path = response_body["data"]["attributes"]["path"]
    except Exception as e:
        logger.error(f"Exception: {e}")
        return {"error": repr(e)}

    # Move all root child files and folders to backup folder
    for path, materialized_path in path_list:
        try:
            response = move_file(node_id, provider, path, new_path, cookies, internal, base_url, is_addon_storage=False)
            if response.status_code != 200 and response.status_code != 201 and response.status_code != 202:
                logger.error(f"Response return error: {response.content}")
                # Rollback
                has_error = True
                error_message = f"{response.status_code} - {response.content}"
                break
            moved_paths.append(("/", path))
        except Exception as e:
            logger.error(f"Exception: {e}")
            has_error = True
            error_message = repr(e)
            break

    if has_error:
        # Rollback
        rollback_folder_movement(node_id, provider, moved_paths, [new_path], cookies, internal, base_url,
                                 is_addon_storage=False)
        return {"error": error_message}
    return {}


def move_bulk_mount_folder_from_backup(node_id, provider, process_start, cookies, internal=True, base_url=WATERBUTLER_URL):
    path_list, backup_path = get_all_child_paths_in_bulk_mount_storage(node_id, provider, f"/backup_{process_start}/",
                                                                       cookies, internal, base_url,
                                                                       get_path_from=f"/backup_{process_start}/")
    if len(path_list) == 0:
        return {}

    # Move files and folders from backup to root
    moved_paths = []
    has_error = False
    error_message = ""
    root_path = "/"
    for path, materialized_path in path_list:
        try:
            response = move_file(node_id, provider, path, root_path, cookies, internal, base_url, is_addon_storage=False)
            if response.status_code != 200 and response.status_code != 201 and response.status_code != 202:
                logger.error(f"Response return error: {response.content}")
                has_error = True
                error_message = f"{response.status_code} - {response.content}"
                break
            moved_paths.append((backup_path, path))
        except Exception as e:
            logger.error(f"Exception: {e}")
            has_error = True
            error_message = repr(e)
            break

    if has_error:
        # Rollback
        rollback_folder_movement(node_id, provider, moved_paths, [], cookies, internal, base_url,
                                 is_addon_storage=False)
        return {"error": error_message}

    # OSF storage: Delete backup folder after moving
    delete_paths(node_id, provider, [backup_path], cookies, internal, base_url)
    return {}


def get_all_child_paths_in_bulk_mount_storage(node_id, provider, file_materialized_path, cookies, internal=True,
                                              base_url=WATERBUTLER_URL, exclude_path_regex="", get_path_from=""):
    path_from_args = None
    try:
        if not file_materialized_path.startswith("/") and not file_materialized_path.endswith("/"):
            return [], path_from_args
        paths = file_materialized_path.split("/")[1:]
        if len(paths) > 0:
            current_path = "/"
            current_materialized_path = "/"
            for index, path in enumerate(paths):
                response = get_file_data(node_id, provider, current_path, cookies, internal=internal,
                                         base_url=base_url, get_file_info=True)
                if response.status_code != 200:
                    return []
                response_body = response.json()
                data = response_body.get("data", [])
                if index == len(paths) - 1:
                    if len(data) != 0:
                        list_file_path = []
                        for item in data:
                            path = item.get("attributes", {}).get("path")
                            materialized_path = item.get("attributes", {}).get("materialized")
                            try:
                                if isinstance(exclude_path_regex, str) and len(exclude_path_regex) != 0:
                                    pattern = re.compile(exclude_path_regex)
                                    if pattern.match(materialized_path):
                                        continue
                            except Exception:
                                continue
                            list_file_path.append((path, materialized_path))
                        return list_file_path, path_from_args
                    else:
                        return []
                else:
                    current_materialized_path = f"{current_materialized_path}{path}/"
                    current_path_info = next((item for item in data if item.get("attributes", {}).get("materialized") ==
                                              current_materialized_path), None)
                    if current_path_info is None:
                        return [], path_from_args

                    current_path = current_path_info["attributes"]["path"]
                    if current_path_info["attributes"]["materialized"] == get_path_from:
                        path_from_args = current_path
    except Exception:
        return [], path_from_args


def rollback_folder_movement(node_id, provider, moved_paths, created_folder_paths, cookies, internal=True,
                             base_url=WATERBUTLER_URL, is_addon_storage=True):
    # Move files and folder back
    for path, new_path in moved_paths:
        try:
            move_file(node_id, provider, new_path, path, cookies, internal, base_url, is_addon_storage)
        except Exception as e:
            logger.error(f"Exception: {e}")

    # Delete folders created by moving files and folders
    delete_paths(node_id, provider, created_folder_paths, cookies, internal, base_url)


def delete_paths(node_id, provider, paths, cookies, internal=True, base_url=WATERBUTLER_URL):
    for path in paths:
        try:
            delete_file(node_id, provider, path, cookies, internal, base_url)
        except Exception as e:
            logger.error(f"Exception: {e}")


def delete_file(node_id, provider, file_path, cookies, internal=True, base_url=WATERBUTLER_URL):
    destination_storage_backup_meta_api = waterbutler_api_url_for(node_id, provider, path=file_path,
                                                                  _internal=internal, base_url=base_url)
    return requests.delete(destination_storage_backup_meta_api,
                           headers={'content-type': 'application/json'},
                           cookies=cookies)


def delete_all_files_except_backup(node_id, provider, cookies, internal=True, base_url=WATERBUTLER_URL):
    # In add-on institutional storage: Delete files, except the backup folder.
    regex = "^\\/backup_\\d{8}T\\d{6}\\/.*$"
    list_not_backup_paths = []
    try:
        response = get_file_data(node_id, provider, "/", cookies, internal=internal,
                                 base_url=base_url, get_file_info=True)
        if response.status_code != 200:
            return []
        response_body = response.json()
        data = response_body.get("data")
        if len(data) != 0:
            for item in data:
                path = item.get("attributes", {}).get("path")
                materialized_path = item.get("attributes", {}).get("materialized")
                kind = item.get("attributes", {}).get("kind")

                try:
                    pattern = re.compile(regex)
                    if pattern.match(materialized_path):
                        continue
                except:
                    continue

                if kind == "file" or kind == "folder":
                    list_not_backup_paths.append(path)
    except (requests.ConnectionError, requests.Timeout) as e:
        logger.error(f"Connection error: {e}")
        raise e
    except:
        pass

    # Delete all paths
    for path in list_not_backup_paths:
        try:
            delete_file(node_id, provider, path, cookies, internal, base_url)
        except (requests.ConnectionError, requests.Timeout) as e:
            logger.error(f"Connection error: {e}")
            raise e
        except:
            continue


def validate_export_data(data_json):
    try:
        schema = from_json('file-info-schema.json')
        jsonschema.validate(data_json, schema)
        return True
    except jsonschema.ValidationError:
        return False


def float_or_None(x):
    try:
        return float(x)
    except ValueError:
        return None


def process_data_information(list_data):
    list_data_version = []
    for item in list_data:
        for file_version in item['version']:
            current_data = {**item, 'version': file_version, 'tags': ', '.join(item['tags'])}
            list_data_version.append(current_data)
    return list_data_version


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
        xfl, yfl = float_or_None(x), float_or_None(y)
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
        d[i] = deep_diff(y[i], x_val, parent_key=i, exclude_keys=exclude_keys, epsilon_keys=epsilon_keys) if flipped else deep_diff(x_val, y[i],
                                                                                                                                    parent_key=i,
                                                                                                                                    exclude_keys=exclude_keys,
                                                                                                                                    epsilon_keys=epsilon_keys)

    for i in range(len(x), len(y)):
        d[i] = (y[i], None) if flipped else (None, y[i])

    return None if all(map(lambda x: x is None, d)) else d


def check_diff_between_version(list_version_a, list_version_b):
    for i in range(len(list_version_a)):
        if list_version_a[i]['identifier'] != list_version_b[i]['identifier']:
            return True, 'Missing file version', list_version_b[i]
        check_diff = deep_diff(list_version_a[i], list_version_b[i])
        if check_diff:
            list_diff = list(check_diff)
            text_error = ', '.join(list_diff) + 'not match'
            return True, text_error, list_version_a[i]
        return False, '', None


def count_files_ng_ok(exported_file_info, storage_file_info):
    data = {
        'NG': 0,
        'OK': 0,
    }
    list_file_ng = []
    count_files = 0
    exported_file_versions = process_data_information(exported_file_info['files'])
    storage_file_versions = process_data_information(storage_file_info['files'])
    for file_a in exported_file_versions:
        file_is_check = False
        version_a = [file_a['version']]
        for file_b in storage_file_versions:
            version_b = [file_b['version']]
            if file_b['id'] == file_a['id'] and file_b['version']['identifier'] == file_a['version']['identifier']:
                file_is_check = True
                is_diff, message, file_version = check_diff_between_version(version_a, version_b)
                if not is_diff:
                    data['OK'] += 1
                else:
                    data['NG'] += 1
                    ng_content = {
                        'path': file_a['materialized_path'],
                        'size': file_version['size'],
                        'version_id': file_version['identifier'],
                        'reason': message,
                    }
                    list_file_ng.append(ng_content)
                count_files += 1
                break
        if not file_is_check:
            data['NG'] += 1
            ng_content = {
                'path': file_a['materialized_path'],
                'size': file_a['size'],
                'version_id': 0,
                'reason': 'File is not exist',
            }
            list_file_ng.append(ng_content)
            count_files += 1
    data['Total'] = count_files
    data['list_file_ng'] = list_file_ng if len(list_file_ng) <= 10 else list_file_ng[:10]
    return data
