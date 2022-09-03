# -*- coding: utf-8 -*-
import inspect  # noqa
import json  # noqa
import logging  # noqa
from copy import deepcopy

import jsonschema
import requests
import re
from datetime import datetime
from django.db.models import Q
from rest_framework import status as http_status

from addons.base.institutions_utils import KEYNAME_BASE_FOLDER
from addons.nextcloudinstitutions import KEYNAME_NOTIFICATION_SECRET
from addons.nextcloudinstitutions.models import NextcloudInstitutionsProvider
from addons.osfstorage.models import Region
from admin.base.schemas.utils import from_json
from admin.rdm_addons.utils import get_rdm_addon_option
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
    'process_data_infomation',
    'get_files_from_waterbutler',
    'validate_export_data',
    'get_file_info_json',
    'write_json_file',
    'read_json_file',
    'check_diff_between_version',
]


def read_json_file(file_path):
    """Read json from a file

    Args:
        file_path: the full path of json file

    Returns:
        json data
    """
    with open(file_path, "r", encoding='utf-8') as read_file:
        try:
            input_data = json.load(read_file)
            return input_data
        except Exception as exc:
            raise Exception(f"Cannot read json file. Exception: {str(exc)}")


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


def get_two_addon_options(institution_id, allowed_check=True):
    # Todo: recheck
    # avoid "ImportError: cannot import name"
    from addons.dropboxbusiness.models import (
        DropboxBusinessFileaccessProvider,
        DropboxBusinessManagementProvider,
    )
    fileaccess_addon_option = get_rdm_addon_option(institution_id, DropboxBusinessFileaccessProvider.short_name, create=False)
    management_addon_option = get_rdm_addon_option(institution_id, DropboxBusinessManagementProvider.short_name, create=False)

    if fileaccess_addon_option is None or management_addon_option is None:
        return None
    if allowed_check and not fileaccess_addon_option.is_allowed:
        return None

    # NOTE: management_addon_option.is_allowed is ignored.
    return fileaccess_addon_option, management_addon_option


def test_dropboxbusiness_connection(institution):
    # Todo: recheck
    from addons.dropboxbusiness import utils as dropboxbusiness_utils

    fm = get_two_addon_options(institution.id, allowed_check=False)

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


def save_dropboxbusiness_credentials(institution, storage_name, provider_name):
    test_connection_result = test_dropboxbusiness_connection(institution)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    wb_credentials, wb_settings = wd_info_for_institutions(provider_name)
    update_storage_location(institution.guid, storage_name, wb_credentials, wb_settings)

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
    wb_credentials["external_account"] = external_account
    wb_settings["extended"] = extended

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


def process_data_infomation(list_data):
    list_data_version = []
    for item in list_data:
        for file_version in item['version']:
            current_data = {**item, 'version': file_version, 'tags': ', '.join(item['tags'])}
            list_data_version.append(current_data)
    return list_data_version


def get_files_from_waterbutler(pid, provider, path, request_cookie):
    content = None
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
    folder = waterbutler_settings["storage"]["folder"]
    try:
        if isinstance(folder, str) or not folder["encrypt_uploads"]:
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


def get_export_data_json(export_id):
    # Get export data
    export_data = ExportData.objects.filter(id=export_id).first()
    # Get region by id
    guid = export_data.source.guid
    # Get Institution by guid
    institution = Institution.objects.filter(_id=guid).first()
    if institution is None or export_data is None:
        return None
    provider_name = export_data.source.waterbutler_settings['storage']['provider']
    if provider_name == 'filesystem':
        provider_name = 'NII Storage'
    export_data = {
        'institution': {
            'institution_id': institution.id,
            'institution_guid': guid,
            'institution_name': institution.name,
        },
        'export_start': export_data.process_start.strftime('%Y-%m-%d %H:%M:%S'),
        'export_end': export_data.process_end.strftime('%Y-%m-%d %H:%M:%S'),
        'storage': {
            'name': export_data.source.name,
            'type': provider_name,
        },
        'projects_numb': export_data.project_number,
        'files_numb': export_data.file_number,
        'size': export_data.total_size,
        'file_path': export_data.get_export_data_file_path(guid),
    }
    return export_data


def get_file_info_json(source_id):
    # Get region by id
    region = Region.objects.filter(id=source_id).first()
    # Get Institution by guid
    institution = Institution.objects.filter(_id=region.guid).first()
    if region is None or institution is None:
        return None

    data_rs = {
        'institution': {
            'institution_id': institution.id,
            'institution_guid': institution.guid,
            'institution_name': institution.name,
        }
    }

    # Get list FileVersion by region_id(source_id)
    list_fileversion_id = FileVersion.objects.filter(region_id=source_id).values_list('id', flat=True)

    # Get list_basefilenode_id by list_fileversion_id above via the BaseFileVersionsThrough model
    list_basefilenode_id = BaseFileVersionsThrough.objects.filter(
        fileversion_id__in=list_fileversion_id).values_list('basefilenode_id', flat=True)

    # Get list project id
    list_project_id = institution.nodes.filter(category='project').values_list('id', flat=True)

    # Get list_basefielnode by list_basefilenode_id above
    list_basefielnode = BaseFileNode.objects.filter(id__in=list_basefilenode_id, target_object_id__in=list_project_id,
                                                    deleted=None)
    list_file = []
    # Loop every basefilenode in list_basefielnode for get data
    for basefilenode in list_basefielnode:
        # Get file's tag
        list_tags = []
        if not basefilenode._state.adding:
            list_tags = list(basefilenode.tags.filter(system=False).values_list('name', flat=True))

        # Get project's data by basefilenode.target_object_id
        project = AbstractNode.objects.get(id=basefilenode.target_object_id)
        basefilenode_info = {
            'id': basefilenode.id,
            'path': basefilenode.path,
            'materialized_path': basefilenode.materialized_path,
            'name': basefilenode.name,
            'size': 0,
            'created_at': basefilenode.created.strftime('%Y-%m-%d %H:%M:%S'),
            'modified_at': basefilenode.modified.strftime('%Y-%m-%d %H:%M:%S'),
            'tags': list_tags,
            'location': {},
            'project': {
                'id': Guid.objects.get(object_id=project.id)._id,
                'name': project.title,
            },
            'version': [],
            'timestamp': {},
        }

        # Get fileversion_id and version_name by basefilenode_id in the BaseFileVersionsThrough model
        list_basefileversion = BaseFileVersionsThrough.objects.filter(
            basefilenode_id=basefilenode.id).order_by('fileversion_id')

        list_fileversion = []

        # Loop every file version of every basefilenode by basefilenode.id
        for item in list_basefileversion:
            # get the file version by id
            fileversion = FileVersion.objects.get(id=item.fileversion_id)

            # Get file version's creator
            creator = OSFUser.objects.get(id=fileversion.creator_id)
            fileversion_data = {
                'identifier': fileversion.identifier,
                'created_at': fileversion.created.strftime('%Y-%m-%d %H:%M:%S'),
                'size': fileversion.size,
                'version_name': basefilenode.name,
                'contributor': creator.username,
                'metadata': fileversion.metadata,
                'location': fileversion.location,
            }
            list_fileversion.append(fileversion_data)
        basefilenode_info['version'] = list_fileversion
        basefilenode_info['size'] = list_fileversion[-1]['size']
        basefilenode_info['location'] = list_fileversion[-1]['location']
        list_file.append(basefilenode_info)

        # Get timestamp by project_id and file_id
        timestamp = RdmFileTimestamptokenVerifyResult.objects.filter(project_id=project.id,
                                                                     file_id=basefilenode.id).first()
        if timestamp:
            basefilenode_info['timestamp'] = {
                'timestamp_token': timestamp.timestamp_token,
                'verify_user': timestamp.verify_user,
                'verify_date': timestamp.verify_date,
                'updated_at': timestamp.verify_file_created_at,
            }
    data_rs['files'] = list_file
    return data_rs


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
                  get_file_info=False, version=None):
    if get_file_info:
        file_url = waterbutler_api_url_for(node_id, provider, path=file_path, _internal=internal, version=version,
                                           base_url=base_url, meta="")
    else:
        file_url = waterbutler_api_url_for(node_id, provider, path=file_path, _internal=internal, version=version,
                                           base_url=base_url)
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


def download_then_upload_file(download_node_id, upload_node_id, download_provider, upload_provider, download_path, upload_path,
                              cookies, download_base_url=WATERBUTLER_URL, upload_base_url=WATERBUTLER_URL, version=None):
    # Download file by version
    is_download_url_internal = download_base_url == WATERBUTLER_URL
    response = get_file_data(download_node_id, download_provider, download_path,
                             cookies, is_download_url_internal, download_base_url, version)
    if response.status_code != 200:
        return None
    download_data = response.content

    # Upload downloaded file to new storage
    is_upload_url_internal = upload_base_url == WATERBUTLER_URL
    response_body = upload_file_path(upload_node_id, upload_provider, upload_path,
                                     download_data, cookies, is_upload_url_internal, upload_base_url)
    if response_body is None:
        return None
    return response_body


def move_file(node_id, provider, source_file_path, destination_file_path, cookies,
              internal=True, base_url=WATERBUTLER_URL):
    move_old_data_url = waterbutler_api_url_for(node_id, provider, path=source_file_path, _internal=internal,
                                                base_url=base_url)
    destination_file_path = destination_file_path[1:] if destination_file_path.startswith("/") else destination_file_path
    request_body = {
        "action": "move",
        "path": "/",
        "rename": destination_file_path,
    }
    return requests.post(move_old_data_url,
                         headers={'content-type': 'application/json'},
                         cookies=cookies,
                         json=request_body)


def move_folder_to_backup(node_id, provider, process_start, cookies, internal=True, base_url=WATERBUTLER_URL):
    path_list, root_child_folders = get_all_file_paths(node_id, provider, "/", cookies, internal, base_url,
                                                       exclude_path_regex="^\\/backup_\\d{8}T\\d{6}\\/.*$")
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
            response = move_file(node_id, provider, path, new_path, cookies, internal, base_url)
            if response.status_code != 200 and response.status_code != 201 and response.status_code != 202:
                logger.error(f"Response return error: {response.content}")
                # Rollback
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
        rollback_folder_movement(node_id, provider, moved_paths, created_folder_paths, cookies,
                                 internal, base_url)
        return {"error": error_message}

    # S3: Clean root folders after moving
    delete_folder_after_move(node_id, provider, root_child_folders, cookies, internal, base_url)
    return {}


def move_folder_from_backup(node_id, provider, process_start, cookies, internal=True, base_url=WATERBUTLER_URL):
    path_list, root_child_folders = get_all_file_paths(node_id, provider, "/", cookies, internal, base_url,
                                                       include_path_regex=f"^\\/backup_{process_start}\\/.*$")

    # Move file
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
            response = move_file(node_id, provider, path, new_path, cookies, internal, base_url)
            if response.status_code != 200 and response.status_code != 201 and response.status_code != 202:
                logger.error(f"Response return error: {response.content}")
                # Rollback
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
        rollback_folder_movement(node_id, provider, moved_paths, created_folder_paths, cookies,
                                 internal, base_url)
        return {"error": error_message}

    # S3: Clean root folders after moving
    delete_folder_after_move(node_id, provider, root_child_folders, cookies, internal, base_url)
    return {}


def get_all_file_paths(node_id, provider, file_path, cookies, internal=True, base_url=WATERBUTLER_URL,
                       include_path_regex="", exclude_path_regex=""):
    try:
        response = get_file_data(node_id, provider, file_path, cookies, internal=internal,
                                 base_url=base_url, get_file_info=True)
        if response.status_code != 200:
            return []
        response_body = response.json()
        data = response_body["data"]
        if len(data) != 0:
            list_file_path = []
            root_child_folders = []
            for item in data:
                path = item["attributes"]["path"]
                kind = item["attributes"]["kind"]

                try:
                    if isinstance(include_path_regex, str) and len(include_path_regex) != 0:
                        pattern = re.compile(include_path_regex)
                        if not pattern.match(path):
                            continue
                    if isinstance(exclude_path_regex, str) and len(exclude_path_regex) != 0:
                        pattern = re.compile(exclude_path_regex)
                        if pattern.match(path):
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
                    sub_file_paths, _ = get_all_file_paths(node_id, provider, path, cookies, internal, base_url)
                    list_file_path.extend(sub_file_paths)

            return list_file_path, root_child_folders
        else:
            return [file_path], []
    except Exception:
        return [], []


def rollback_folder_movement(node_id, provider, moved_paths, created_folder_paths, cookies,
                             internal=True, base_url=WATERBUTLER_URL):
    # Move files and folder back
    for path, new_path in moved_paths:
        try:
            move_file(node_id, provider, new_path, path, cookies, internal, base_url)
        except Exception as e:
            logger.error(f"Exception: {e}")

    # S3: Delete folders created by moving files and folders
    for path in created_folder_paths:
        try:
            delete_file(node_id, provider, path, cookies, internal, base_url)
        except Exception as e:
            logger.error(f"Exception: {e}")


def delete_folder_after_move(node_id, provider, root_child_folders, cookies,
                             internal=True, base_url=WATERBUTLER_URL):
    for path in root_child_folders:
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
        data = response_body["data"]
        if len(data) != 0:
            for item in data:
                path = item["attributes"]["path"]
                kind = item["attributes"]["kind"]

                try:
                    pattern = re.compile(regex)
                    if pattern.match(path):
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


def deep_diff(x, y, parent_key=None, exclude_keys=[], epsilon_keys=[]):
    """
    Find the difference between 2 dictionary
    Take the deep diff of JSON-like dictionaries
    No warranties when keys, or values are None
    """
    EPSILON = 0.5
    rho = 1 - EPSILON

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
        if check_diff is None:
            return False, '', None
        else:
            list_diff = list(check_diff)
            text_error = ', '.join(list_diff) + 'not match'
            return True, text_error, list_version_a[i]
