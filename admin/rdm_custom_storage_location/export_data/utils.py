# -*- coding: utf-8 -*-
import inspect  # noqa
import json  # noqa
import logging  # noqa

import jsonschema
import numpy as np
import requests
from django.db import connection
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
    ExportDataLocation,
    Institution,
    FileVersion,
    BaseFileVersionsThrough,
    BaseFileNode,
    AbstractNode,
    OSFUser,
    RdmFileTimestamptokenVerifyResult
)
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
    'get_list_file_info',
    'get_files_from_waterbutler',
    'delete_file_export',
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


def get_list_file_info(pid, provider, path, request_cookie, guid=None, process_start=None):
    content_data, status_code = get_files_from_waterbutler(pid, provider, path, request_cookie)
    if status_code != 200:
        return None, status_code
    return get_list_file_detail(content_data, pid, provider, request_cookie, guid, process_start)


def delete_file_export(pid, provider, path, request_cookie):
    status_code = 555
    try:
        url = waterbutler_api_url_for(
            pid, provider, path='/{}'.format(path), _internal=True
        )
        response = requests.delete(
            url,
            headers={'content-type': 'application/json'},
            cookies=request_cookie
        )
    except Exception:
        return status_code
    status_code = response.status_code
    response.close()
    return status_code


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


def get_info_export_data(region_id):
    # Get region by id
    region = Region.objects.filter(id=region_id).first()
    # Get Institution by guid
    institution = Institution.objects.filter(_id=region._id).first()
    if region is None or institution is None:
        return None

    data_rs = {
        'institution': {
            'institution_id': institution.id,
            'institution_guid': institution._id,
            'institution_name': institution.name,
        }
    }

    # Get list FileVersion by region_id(source_id)
    list_fileversion_id = FileVersion.objects.filter(region_id=region_id).values_list('id', flat=True)

    # Get list_basefilenode_id by list_fileversion_id above via the BaseFileVersionsThrough model
    list_basefileversion = BaseFileVersionsThrough.objects.filter(
        fileversion_id__in=list_fileversion_id).values_list('basefilenode_id', 'version_name')
    list_basefilenode_id, list_file_verson_name = zip(*list_basefileversion)

    # Gte list_basefielnode by list_basefilenode_id above
    list_basefielnode = BaseFileNode.objects.filter(id__in=list_basefilenode_id, deleted=None)
    list_file = []
    cursor = connection.cursor()
    # Loop every basefilenode in list_basefielnode for get data
    for basefilenode in list_basefielnode:
        query_string = """
                    select tag.name from osf_basefilenode_tags as bastag
                    inner join osf_tag as tag
                    on tag.id = bastag.tag_id
                    where bastag.basefilenode_id = {basefilenode_id}
                    """.format(basefilenode_id=basefilenode.id)
        cursor.execute(query_string)
        result = np.asarray(cursor.fetchall())
        list_tags = []
        if result.shape != (0,):
            for tag in result[:, 0]:
                list_tags.append(tag)
        # Get project's data by basefilenode.target_object_id
        project = AbstractNode.objects.get(id=basefilenode.target_object_id)
        basefilenode_info = {
            'id': basefilenode.id,
            'path': basefilenode.path,
            'materialized_path': basefilenode.materialized_path,
            'name': basefilenode.name,
            'size': 0,
            'created_at': basefilenode.created.strftime("%Y-%m-%d %H:%M:%S"),
            'modified_at': basefilenode.modified.strftime("%Y-%m-%d %H:%M:%S"),
            'tags': list_tags,
            'location': {},
            'project': {
                'id': project.id,
                'name': project.title,
            },
            'version': [],
            'timestamp': {},
        }

        # Get fileversion_id and version_name by basefilenode_id in the BaseFileVersionsThrough model
        list_fileversion_data = BaseFileVersionsThrough.objects.filter(
            basefilenode_id=basefilenode.id).values_list('fileversion_id', 'version_name')
        list_fileversion_id, list_fileverson_name = zip(*list_fileversion_data)
        dict_file_version_name = dict(zip(list_fileversion_id, list_fileverson_name))

        list_fileversion = []

        # Loop every file version of every basefilenode by basefilenode.id
        for filerversion_id, fileverson_name in dict_file_version_name.items():
            # get the file version by id
            filerversion = FileVersion.objects.get(id=filerversion_id)

            # Get file version's creator
            creator = OSFUser.objects.get(id=filerversion.creator_id)
            fileverison_data = {
                'identifier': filerversion.identifier,
                'created_at': filerversion.created.strftime("%Y-%m-%d %H:%M:%S"),
                'size': filerversion.size,
                'version_name': fileverson_name,
                'contributor': creator.username,
                'metadata': filerversion.metadata,
                'location': filerversion.location,
            }
            list_fileversion.append(fileverison_data)
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
