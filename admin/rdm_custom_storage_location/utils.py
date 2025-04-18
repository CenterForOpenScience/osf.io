# -*- coding: utf-8 -*-

import inspect  # noqa
import logging
import traceback

from boxsdk import Client as BoxClient, OAuth2
from boxsdk.exception import BoxAPIException
from furl import furl
from rest_framework import status as http_status
import requests
from swiftclient import exceptions as swift_exceptions
import os
import owncloud
from django.core.exceptions import ValidationError

from admin.rdm_addons.utils import get_rdm_addon_option
from addons.googledrive.client import GoogleDriveClient
from addons.osfstorage.models import Region
from addons.box import settings as box_settings
from addons.owncloud import settings as owncloud_settings
from addons.nextcloud import settings as nextcloud_settings
from addons.s3 import utils as s3_utils
from addons.s3compat import utils as s3compat_utils
from addons.s3compatb3 import utils as s3compatb3_utils
from addons.swift import settings as swift_settings, utils as swift_utils
from addons.swift.provider import SwiftProvider
from addons.dropboxbusiness import utils as dropboxbusiness_utils
from addons.nextcloudinstitutions.models import NextcloudInstitutionsProvider
from addons.nextcloudinstitutions import settings as nextcloudinstitutions_settings
from addons.nextcloudinstitutions import KEYNAME_NOTIFICATION_SECRET
from addons.s3compatinstitutions.models import S3CompatInstitutionsProvider
from addons.s3compatinstitutions import settings as s3compatinstitutions_settings
from addons.ociinstitutions.models import OCIInstitutionsProvider
from addons.ociinstitutions import settings as ociinstitutions_settings
from addons.onedrivebusiness.client import OneDriveBusinessClient
from addons.base.institutions_utils import (KEYNAME_BASE_FOLDER,
                                            KEYNAME_USERMAP,
                                            KEYNAME_USERMAP_TMP,
                                            sync_all)
from framework.exceptions import HTTPError
from website import settings as osf_settings
from osf.models import Node, OSFUser, ProjectStorageType, UserQuota
from osf.models.external import ExternalAccountTemporary, ExternalAccount
from osf.utils import external_util
import datetime

from website.util import inspect_info  # noqa
from website.util.quota import update_node_storage, update_user_used_quota

logger = logging.getLogger(__name__)

providers = None

enabled_providers_forinstitutions_list = [
    'dropboxbusiness',
    'nextcloudinstitutions',
    's3compatinstitutions',
    'ociinstitutions',
    'onedrivebusiness',
]

enabled_providers_list = [
    's3', 'osfstorage',
    'swift', 's3compat',
]
enabled_providers_list.extend(enabled_providers_forinstitutions_list)

no_storage_name_providers = ['osfstorage', 'onedrivebusiness']

def have_storage_name(provider_name):
    return provider_name not in no_storage_name_providers


def get_providers(available_list=None):
    provider_list = []
    for provider in osf_settings.ADDONS_AVAILABLE:
        if 'storage' in provider.categories and provider.short_name in enabled_providers_list:
            provider.icon_url_admin = \
                '/custom_storage_location/icon/{}/comicon.png'.format(provider.short_name)
            provider.modal_path = get_modal_path(provider.short_name)
            provider_list.append(provider)
    provider_list.sort(key=lambda x: x.full_name.lower())
    if isinstance(available_list, list):
        return [addon for addon in provider_list if addon.short_name in available_list]
    return provider_list

def get_addon_by_name(addon_short_name):
    """get Addon object from Short Name."""
    for addon in osf_settings.ADDONS_AVAILABLE:
        if addon.short_name == addon_short_name:
            return addon

def get_modal_path(short_name):
    base_path = os.path.join('rdm_custom_storage_location', 'providers')
    return os.path.join(base_path, '{}_modal.html'.format(short_name))

def get_oauth_info_notification(institution_id, provider_short_name):
    temp_external_account = ExternalAccountTemporary.objects.filter(
        _id=institution_id, provider=provider_short_name
    ).first()
    if temp_external_account and \
            temp_external_account.modified >= datetime.datetime.now(
                temp_external_account.modified.tzinfo
            ) - datetime.timedelta(seconds=60 * 30):
        return {
            'display_name': temp_external_account.display_name,
            'oauth_key': temp_external_account.oauth_key,
            'provider': temp_external_account.provider,
            'provider_id': temp_external_account.provider_id,
            'provider_name': temp_external_account.provider_name,
        }

def set_allowed(institution, provider_name, is_allowed):
    addon_option = get_rdm_addon_option(institution.id, provider_name)
    addon_option.is_allowed = is_allowed
    addon_option.save()
    # NOTE: ExternalAccounts is not cleared even if other storage is selected.
    # if not is_allowed:
    #     addon_option.external_accounts.clear()

def change_allowed_for_institutions(institution, provider_name):
    if provider_name in enabled_providers_forinstitutions_list:
        set_allowed(institution, provider_name, True)

    # disable other storages for Institutions
    for p in get_providers():
        if p.short_name == provider_name:
            continue  # skip this provider
        if p.for_institutions:
            set_allowed(institution, p.short_name, False)

def set_default_storage(institution_id):
    default_region = Region.objects.first()
    try:
        region = Region.objects.get(_id=institution_id)
        # copy
        region.name = default_region.name
        region.waterbutler_credentials = default_region.waterbutler_credentials
        region.waterbutler_settings = default_region.waterbutler_settings
        region.waterbutler_url = default_region.waterbutler_url
        region.mfr_url = default_region.mfr_url
        region.save()
    except Region.DoesNotExist:
        region = Region.objects.create(
            _id=institution_id,
            name=default_region.name,
            waterbutler_credentials=default_region.waterbutler_credentials,
            waterbutler_settings=default_region.waterbutler_settings,
            waterbutler_url=default_region.waterbutler_url,
            mfr_url=default_region.mfr_url,
        )
    return region

def update_storage(institution_id, storage_name, wb_credentials, wb_settings):
    try:
        region = Region.objects.get(_id=institution_id)
    except Region.DoesNotExist:
        default_region = Region.objects.first()
        region = Region.objects.create(
            _id=institution_id,
            name=storage_name,
            waterbutler_credentials=wb_credentials,
            waterbutler_url=default_region.waterbutler_url,
            mfr_url=default_region.mfr_url,
            waterbutler_settings=wb_settings,
        )
    else:
        region.name = storage_name
        region.waterbutler_credentials = wb_credentials
        region.waterbutler_settings = wb_settings
        region.save()
    return region

def update_nodes_storage(institution):
    for node in Node.objects.filter(affiliated_institutions=institution.id):
        update_node_storage(node)
        storage_type = ProjectStorageType.objects.filter(node=node)
        storage_type.update(storage_type=ProjectStorageType.CUSTOM_STORAGE)
    for user in OSFUser.objects.filter(affiliated_institutions=institution.id):
        update_user_used_quota(user, storage_type=UserQuota.CUSTOM_STORAGE, is_recalculating_quota=True)

def transfer_to_external_account(user, institution_id, provider_short_name):
    temp_external_account = ExternalAccountTemporary.objects.filter(_id=institution_id, provider=provider_short_name).first()
    account, _ = ExternalAccount.objects.get_or_create(
        provider=temp_external_account.provider,
        provider_id=temp_external_account.provider_id,
    )

    # ensure that provider_name is correct
    account.provider_name = temp_external_account.provider_name
    # required
    account.oauth_key = temp_external_account.oauth_key
    # only for OAuth1
    account.oauth_secret = temp_external_account.oauth_secret
    # only for OAuth2
    account.expires_at = temp_external_account.expires_at
    account.refresh_token = temp_external_account.refresh_token
    account.date_last_refreshed = temp_external_account.date_last_refreshed
    # additional information
    account.display_name = temp_external_account.display_name
    account.profile_url = temp_external_account.profile_url
    account.save()

    temp_external_account.delete()

    # add it to the user's list of ``ExternalAccounts``
    if not user.external_accounts.filter(id=account.id).exists():
        user.external_accounts.add(account)
        user.save()
    return account

def oauth_validation(provider, institution_id, folder_id):
    """Checks if the folder_id is not empty, and that a temporary external account exists
    in the database.
    """
    if not folder_id:
        return ({
            'message': 'Folder ID is missing.'
        }, http_status.HTTP_400_BAD_REQUEST)

    if not ExternalAccountTemporary.objects.filter(_id=institution_id, provider=provider).exists():
        return ({
            'message': 'Oauth data was not found. Please reload the page and try again.'
        }, http_status.HTTP_400_BAD_REQUEST)

    return True

def test_s3_connection(access_key, secret_key, bucket):
    """Verifies new external account credentials and adds to user's list"""
    if not (access_key and secret_key and bucket):
        return ({
            'message': 'All the fields above are required.'
        }, http_status.HTTP_400_BAD_REQUEST)
    user_info = s3_utils.get_user_info(access_key, secret_key)
    if not user_info:
        return ({
            'message': 'Unable to access account.\n'
            'Check to make sure that the above credentials are valid,'
            'and that they have permission to list buckets.'
        }, http_status.HTTP_400_BAD_REQUEST)

    if not s3_utils.can_list(access_key, secret_key):
        return ({
            'message': 'Unable to list buckets.\n'
            'Listing buckets is required permission that can be changed via IAM'
        }, http_status.HTTP_400_BAD_REQUEST)

    if not s3_utils.bucket_exists(access_key, secret_key, bucket):
        return ({
            'message': 'Invalid bucket.'
        }, http_status.HTTP_400_BAD_REQUEST)

    s3_response = {
        'id': user_info.id,
        'display_name': user_info.display_name,
        'Owner': user_info.Owner,
    }

    return ({
        'message': 'Credentials are valid',
        'data': s3_response
    }, http_status.HTTP_200_OK)

def test_s3compat_connection(host_url, access_key, secret_key, bucket):
    host = host_url.rstrip('/').replace('https://', '').replace('http://', '')
    if not (host and access_key and secret_key and bucket):
        return ({
            'message': 'All the fields above are required.'
        }, http_status.HTTP_400_BAD_REQUEST)

    try:
        user_info = s3compat_utils.get_user_info(host, access_key, secret_key)
        e_message = ''
    except Exception as e:
        user_info = None
        e_message = traceback.format_exception_only(type(e), e)[0].rstrip('\n')
    if not user_info:
        return ({
            'message': 'Unable to access account.\n'
            'Check to make sure that the above credentials are valid, '
            'and that they have permission to list buckets.',
            'e_message': e_message
        }, http_status.HTTP_400_BAD_REQUEST)

    try:
        res = s3compat_utils.can_list(host, access_key, secret_key)
        e_message = ''
    except Exception as e:
        res = False
        e_message = traceback.format_exception_only(type(e), e)[0].rstrip('\n')
    if not res:
        return ({
            'message': 'Unable to list buckets.\n'
            'Listing buckets is required permission that can be changed via IAM',
            'e_message': e_message
        }, http_status.HTTP_400_BAD_REQUEST)

    try:
        res = s3compat_utils.bucket_exists(host, access_key, secret_key, bucket)
        e_message = ''
    except Exception as e:
        res = False
        e_message = traceback.format_exception_only(type(e), e)[0].rstrip('\n')
    if not res:
        return ({
            'message': 'Invalid bucket.',
            'e_message': e_message
        }, http_status.HTTP_400_BAD_REQUEST)

    return ({
        'message': 'Credentials are valid',
        'data': {
            'id': user_info.id,
            'display_name': user_info.display_name,
        }
    }, http_status.HTTP_200_OK)

def test_s3compatb3_connection(host_url, access_key, secret_key, bucket):
    host = host_url.rstrip('/').replace('https://', '').replace('http://', '')
    if not (host and access_key and secret_key and bucket):
        return ({
            'message': 'All the fields above are required.'
        }, http_status.HTTP_400_BAD_REQUEST)

    try:
        user_info = s3compatb3_utils.get_user_info(host, access_key, secret_key)
        e_message = ''
    except Exception as e:
        user_info = None
        e_message = traceback.format_exception_only(type(e), e)[0].rstrip('\n')
    if not user_info:
        return ({
            'message': 'Unable to access account.\n'
            'Check to make sure that the above credentials are valid, '
            'and that they have permission to list buckets.',
            'e_message': e_message
        }, http_status.HTTP_400_BAD_REQUEST)

    try:
        res = s3compatb3_utils.can_list(host, access_key, secret_key)
        e_message = ''
    except Exception as e:
        res = False
        e_message = traceback.format_exception_only(type(e), e)[0].rstrip('\n')
    if not res:
        return ({
            'message': 'Unable to list buckets.\n'
            'Listing buckets is required permission that can be changed via IAM',
            'e_message': e_message
        }, http_status.HTTP_400_BAD_REQUEST)

    try:
        res = s3compatb3_utils.bucket_exists(host, access_key, secret_key, bucket)
        e_message = ''
    except Exception as e:
        res = False
        e_message = traceback.format_exception_only(type(e), e)[0].rstrip('\n')
    if not res:
        return ({
            'message': 'Invalid bucket.',
            'e_message': e_message
        }, http_status.HTTP_400_BAD_REQUEST)

    return ({
        'message': 'Credentials are valid',
        'data': {
            'id': 'user_info.id',
            'display_name': 'user_info.display_name',
        }
    }, http_status.HTTP_200_OK)

def test_box_connection(institution_id, folder_id):
    validation_result = oauth_validation('box', institution_id, folder_id)
    if isinstance(validation_result, tuple):
        return validation_result

    access_token = ExternalAccountTemporary.objects.get(
        _id=institution_id, provider='box'
    ).oauth_key
    oauth = OAuth2(
        client_id=box_settings.BOX_KEY,
        client_secret=box_settings.BOX_SECRET,
        access_token=access_token
    )
    client = BoxClient(oauth)

    try:
        client.folder(folder_id).get()
    except BoxAPIException:
        return ({
            'message': 'Invalid folder ID.'
        }, http_status.HTTP_400_BAD_REQUEST)

    return ({
        'message': 'Credentials are valid'
    }, http_status.HTTP_200_OK)

def test_googledrive_connection(institution_id, folder_id):
    validation_result = oauth_validation('googledrive', institution_id, folder_id)
    if isinstance(validation_result, tuple):
        return validation_result

    access_token = ExternalAccountTemporary.objects.get(
        _id=institution_id, provider='googledrive'
    ).oauth_key
    client = GoogleDriveClient(access_token)

    try:
        client.folders(folder_id)
    except HTTPError:
        return ({
            'message': 'Invalid folder ID.'
        }, http_status.HTTP_400_BAD_REQUEST)

    return ({
        'message': 'Credentials are valid'
    }, http_status.HTTP_200_OK)

def test_owncloud_connection(host_url, username, password, folder, provider):
    """ This method is valid for both ownCloud and Nextcloud """
    provider_name = None
    provider_setting = None
    if provider == 'owncloud':
        provider_name = 'ownCloud'
        provider_setting = owncloud_settings
    elif provider == 'nextcloud':
        provider_name = 'Nextcloud'
        provider_setting = nextcloud_settings
    elif provider == 'nextcloudinstitutions':
        provider_name = NextcloudInstitutionsProvider.name
        provider_setting = nextcloudinstitutions_settings

    host = use_https(host_url)

    try:
        client = owncloud.Client(host.url, verify_certs=provider_setting.USE_SSL)
        client.login(username, password)
    except requests.exceptions.ConnectionError:
        return ({
            'message': 'Invalid {} server.'.format(provider_name) + host.url
        }, http_status.HTTP_400_BAD_REQUEST)
    except owncloud.owncloud.HTTPResponseError:
        return ({
            'message': '{} Login failed.'.format(provider_name)
        }, http_status.HTTP_401_UNAUTHORIZED)

    try:
        client.list(folder)
    except owncloud.owncloud.HTTPResponseError:
        client.logout()
        return ({
            'message': 'Invalid folder.'
        }, http_status.HTTP_400_BAD_REQUEST)

    client.logout()

    return ({
        'message': 'Credentials are valid'
    }, http_status.HTTP_200_OK)

def test_swift_connection(auth_version, auth_url, access_key, secret_key, tenant_name,
                          user_domain_name, project_domain_name, container):
    """Verifies new external account credentials and adds to user's list"""
    if not (auth_version and auth_url and access_key and secret_key and tenant_name and container):
        return ({
            'message': 'All the fields above are required.'
        }, http_status.HTTP_400_BAD_REQUEST)
    if auth_version == '3' and not user_domain_name:
        return ({
            'message': 'The field `user_domain_name` is required when you choose identity V3.'
        }, http_status.HTTP_400_BAD_REQUEST)
    if auth_version == '3' and not project_domain_name:
        return ({
            'message': 'The field `project_domain_name` is required when you choose identity V3.'
        }, http_status.HTTP_400_BAD_REQUEST)

    user_info = swift_utils.get_user_info(auth_version, auth_url, access_key,
                                    user_domain_name, secret_key, tenant_name,
                                    project_domain_name)

    if not user_info:
        return ({
            'message': 'Unable to access account.\n'
            'Check to make sure that the above credentials are valid, '
            'and that they have permission to list containers.'
        }, http_status.HTTP_400_BAD_REQUEST)

    try:
        _, containers = swift_utils.connect_swift(
            auth_version, auth_url, access_key, user_domain_name, secret_key, tenant_name,
            timeout=swift_settings.TEST_TIMEOUT
        ).get_account()
    except swift_exceptions.ClientException:
        return ({
            'message': 'Unable to list containers.\n'
            'Listing containers is required permission.'
        }, http_status.HTTP_400_BAD_REQUEST)

    if container not in map(lambda c: c['name'], containers):
        return ({
            'message': 'Invalid container name.'
        }, http_status.HTTP_400_BAD_REQUEST)

    provider = SwiftProvider(account=None, auth_version=auth_version,
                             auth_url=auth_url, tenant_name=tenant_name,
                             project_domain_name=project_domain_name,
                             username=access_key,
                             user_domain_name=user_domain_name,
                             password=secret_key)
    swift_response = {
        'id': provider.account.id,
        'display_name': provider.account.display_name,
    }
    return ({
        'message': 'Credentials are valid',
        'data': swift_response
    }, http_status.HTTP_200_OK)

def test_dropboxbusiness_connection(institution):
    fm = dropboxbusiness_utils.get_two_addon_options(institution.id,
                                                     allowed_check=False)
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

def get_onedrivebusiness_folder_id(client, folder_path, parent='root'):
    folder_path_parts = folder_path.rstrip('/').split('/', maxsplit=1)
    folder_name = folder_path_parts[0]
    if folder_name == 'shared':
        return _get_onedrivebusiness_folder_id(client, folder_path_parts[1], parent=parent)
    drive = client.get_drive(me=True)
    drive_client = OneDriveBusinessClient(client.access_token, drive['id'])
    folders = [f for f in drive_client.folders(parent) if f['name'] == folder_name]
    if len(folders) == 0:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    if len(folder_path_parts) == 1:
        return drive['id'] + '\t' + folders[0]['id']
    return drive['id'] + '\t' + _get_onedrivebusiness_folder_id(
        drive_client, folder_path_parts[1], parent=folders[0]['id']
    )

def _get_onedrivebusiness_folder_id(client, folder_path, parent='root'):
    folder_path_parts = folder_path.rstrip('/').split('/', maxsplit=1)
    folder_name = folder_path_parts[0]
    folders = [f for f in client.folders(parent) if f['name'] == folder_name]
    if len(folders) == 0:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    if len(folder_path_parts) == 1:
        return folders[0]['id']
    return _get_onedrivebusiness_folder_id(
        client, folder_path_parts[1], parent=folders[0]['id']
    )

def validate_onedrivebusiness_connection(institution_id, folder_id_or_path):
    validation_result = oauth_validation('onedrivebusiness', institution_id, folder_id_or_path)
    if isinstance(validation_result, tuple):
        return validation_result, None

    access_token = ExternalAccountTemporary.objects.get(
        _id=institution_id, provider='onedrivebusiness'
    ).oauth_key
    client = OneDriveBusinessClient(access_token)

    if folder_id_or_path.startswith('/'):
        try:
            folder_id = get_onedrivebusiness_folder_id(client, folder_id_or_path[1:])
        except HTTPError:
            return ({
                'message': 'Invalid folder Path.'
            }, http_status.HTTP_400_BAD_REQUEST), None
    else:
        try:
            client.folders(folder_id_or_path)
            folder_id = folder_id_or_path
        except HTTPError:
            return ({
                'message': 'Invalid folder ID.'
            }, http_status.HTTP_400_BAD_REQUEST), None

    return ({
        'message': 'Credentials are valid'
    }, http_status.HTTP_200_OK), folder_id

def save_s3_credentials(institution_id, storage_name, access_key, secret_key, bucket, server_side_encryption=False):
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
            'folder': '',
            'encrypt_uploads': server_side_encryption,
            'bucket': bucket,
            'provider': 's3',
            'type': Region.INSTITUTIONS,
        },
    }

    region = update_storage(institution_id, storage_name, wb_credentials, wb_settings)
    external_util.remove_region_external_account(region)

    return ({
        'message': 'Saved credentials successfully!!'
    }, http_status.HTTP_200_OK)

def save_s3compat_credentials(institution_id, storage_name, host_url, access_key, secret_key,
                              bucket, server_side_encryption=False):

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
            'folder': '',
            'encrypt_uploads': server_side_encryption,
            'bucket': bucket,
            'provider': 's3compat',
            'type': Region.INSTITUTIONS,
        }
    }

    region = update_storage(institution_id, storage_name, wb_credentials, wb_settings)
    external_util.remove_region_external_account(region)

    return ({
        'message': 'Saved credentials successfully!!'
    }, http_status.HTTP_200_OK)

def save_s3compatb3_credentials(institution_id, storage_name, host_url, access_key, secret_key,
                              bucket):

    test_connection_result = test_s3compatb3_connection(host_url, access_key, secret_key, bucket)
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
            'provider': 's3compatb3',
            'type': Region.INSTITUTIONS,
        }
    }

    region = update_storage(institution_id, storage_name, wb_credentials, wb_settings)
    external_util.remove_region_external_account(region)

    return ({
        'message': 'Saved credentials successfully!!'
    }, http_status.HTTP_200_OK)

def save_box_credentials(institution_id, user, storage_name, folder_id):
    test_connection_result = test_box_connection(institution_id, folder_id)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    account = transfer_to_external_account(user, institution_id, 'box')
    wb_credentials = {
        'storage': {
            'token': account.oauth_key,
        },
    }
    wb_settings = {
        'storage': {
            'bucket': '',
            'folder': folder_id,
            'provider': 'box',
            'type': Region.INSTITUTIONS,
        }
    }
    region = update_storage(institution_id, storage_name, wb_credentials, wb_settings)
    external_util.set_region_external_account(region, account)

    return ({
        'message': 'OAuth was set successfully'
    }, http_status.HTTP_200_OK)

def save_googledrive_credentials(institution_id, user, storage_name, folder_id):
    test_connection_result = test_googledrive_connection(institution_id, folder_id)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    account = transfer_to_external_account(user, institution_id, 'googledrive')
    wb_credentials = {
        'storage': {
            'token': account.oauth_key,
        },
    }
    wb_settings = {
        'storage': {
            'bucket': '',
            'folder': {
                'id': folder_id
            },
            'provider': 'googledrive',
            'type': Region.INSTITUTIONS,
        }
    }
    region = update_storage(institution_id, storage_name, wb_credentials, wb_settings)
    external_util.set_region_external_account(region, account)

    return ({
        'message': 'OAuth was set successfully'
    }, http_status.HTTP_200_OK)

def save_nextcloud_credentials(institution_id, storage_name, host_url, username, password,
                              folder, provider):
    test_connection_result = test_owncloud_connection(host_url, username, password, folder,
                                                      provider)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    # Ensure that NextCloud uses https
    host = furl()
    host.host = host_url.rstrip('/').replace('https://', '').replace('http://', '')
    host.scheme = 'https'

    wb_credentials = {
        'storage': {
            'host': host.url,
            'username': username,
            'password': password,
        },
    }
    wb_settings = {
        'storage': {
            'bucket': '',
            'folder': '/{}/'.format(folder.strip('/')),
            'verify_ssl': False,
            'provider': provider,
            'type': Region.INSTITUTIONS,
        },
    }

    region = update_storage(institution_id, storage_name, wb_credentials, wb_settings)
    external_util.remove_region_external_account(region)

    return ({
        'message': 'Saved credentials successfully!!'
    }, http_status.HTTP_200_OK)

def save_osfstorage_credentials(institution_id):
    region = set_default_storage(institution_id)
    external_util.remove_region_external_account(region)
    return ({
        'message': 'NII storage was set successfully'
    }, http_status.HTTP_200_OK)

def save_swift_credentials(institution_id, storage_name, auth_version, access_key, secret_key,
                           tenant_name, user_domain_name, project_domain_name, auth_url,
                           container):

    test_connection_result = test_swift_connection(auth_version, auth_url, access_key, secret_key,
        tenant_name, user_domain_name, project_domain_name, container)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    wb_credentials = {
        'storage': {
            'auth_version': auth_version,
            'username': access_key,
            'password': secret_key,
            'tenant_name': tenant_name,
            'user_domain_name': user_domain_name,
            'project_domain_name': project_domain_name,
            'auth_url': auth_url,
        },
    }
    wb_settings = {
        'storage': {
            'bucket': '',
            'folder': '',
            'container': container,
            'provider': 'swift',
            'type': Region.INSTITUTIONS,
        }

    }

    region = update_storage(institution_id, storage_name, wb_credentials, wb_settings)
    external_util.remove_region_external_account(region)

    return ({
        'message': 'Saved credentials successfully!!'
    }, http_status.HTTP_200_OK)

def save_owncloud_credentials(institution_id, storage_name, host_url, username, password,
                              folder, provider):
    test_connection_result = test_owncloud_connection(host_url, username, password, folder,
                                                      provider)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    # Ensure that ownCloud uses https
    host = furl()
    host.host = host_url.rstrip('/').replace('https://', '').replace('http://', '')
    host.scheme = 'https'

    wb_credentials = {
        'storage': {
            'host': host.url,
            'username': username,
            'password': password,
        },
    }
    wb_settings = {
        'storage': {
            'bucket': '',
            'folder': '/{}/'.format(folder.strip('/')),
            'verify_ssl': True,
            'provider': provider,
            'type': Region.INSTITUTIONS,
        },
    }

    region = update_storage(institution_id, storage_name, wb_credentials, wb_settings)
    external_util.remove_region_external_account(region)

    return ({
        'message': 'Saved credentials successfully!!'
    }, http_status.HTTP_200_OK)

def save_onedrivebusiness_credentials(institution_id, user, storage_name, provider_name, folder_id_or_path):
    test_connection_result, folder_id = validate_onedrivebusiness_connection(institution_id, folder_id_or_path)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    account = transfer_to_external_account(user, institution_id, 'onedrivebusiness')
    wb_credentials, wb_settings = wd_info_for_institutions(provider_name)
    wb_settings['root_folder_id'] = folder_id
    region = update_storage(institution_id, storage_name, wb_credentials, wb_settings)
    external_util.set_region_external_account(region, account)

    return ({
        'message': 'OAuth was set successfully'
    }, http_status.HTTP_200_OK)

def wd_info_for_institutions(provider_name, server_side_encryption=False):
    wb_credentials = {
        'storage': {
        },
    }
    wb_settings = {
        'disabled': True,  # used in rubeus.py
        'storage': {
            'provider': provider_name,
            'type': Region.INSTITUTIONS,
        },
    }

    if provider_name == 's3compatinstitutions':
        wb_settings['encrypt_uploads'] = server_side_encryption

    return (wb_credentials, wb_settings)

def use_https(url):
    # Ensure that NextCloud uses https
    host = furl()
    host.host = url.rstrip('/').replace('https://', '').replace('http://', '')
    host.scheme = 'https'
    return host

def save_dropboxbusiness_credentials(institution, storage_name, provider_name):
    test_connection_result = test_dropboxbusiness_connection(institution)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    wb_credentials, wb_settings = wd_info_for_institutions(provider_name)
    region = update_storage(institution._id,  # not institution.id
                            storage_name,
                            wb_credentials, wb_settings)
    external_util.remove_region_external_account(region)
    ### sync_all() is not supported by Dropbox Business Addon
    # sync_all(institution._id, target_addons=[provider_name])

    return ({
        'message': 'Dropbox Business was set successfully!!'
    }, http_status.HTTP_200_OK)

def save_basic_storage_institutions_credentials_common(
        institution, storage_name, folder, provider_name, provider, separator=':', extended_data=None, server_side_encryption=False):
    try:
        provider.account.save()
    except ValidationError:
        host = provider.host
        username = provider.username
        password = provider.password
        # ... or get the old one
        provider.account = ExternalAccount.objects.get(
            provider=provider_name,
            provider_id='{}{}{}'.format(host, separator, username)
        )
        if provider.account.oauth_key != password:
            provider.account.oauth_key = password
            provider.account.save()

    # Storage Addons for Institutions must have only one ExternalAccont.
    rdm_addon_option = get_rdm_addon_option(institution.id, provider_name)
    if rdm_addon_option.external_accounts.count() > 0:
        rdm_addon_option.external_accounts.clear()
    rdm_addon_option.external_accounts.add(provider.account)

    rdm_addon_option.extended[KEYNAME_BASE_FOLDER] = folder
    if type(extended_data) is dict:
        rdm_addon_option.extended.update(extended_data)
    rdm_addon_option.save()

    wb_credentials, wb_settings = wd_info_for_institutions(provider_name, server_side_encryption)
    region = update_storage(institution._id,  # not institution.id
                            storage_name,
                            wb_credentials, wb_settings)
    external_util.remove_region_external_account(region)

    save_usermap_from_tmp(provider_name, institution)
    sync_all(institution._id, target_addons=[provider_name])

    return ({
        'message': 'Saved credentials successfully!!'
    }, http_status.HTTP_200_OK)

def save_nextcloudinstitutions_credentials(
        institution, storage_name, host_url, username, password, folder, notification_secret, provider_name):
    test_connection_result = test_owncloud_connection(
        host_url, username, password, folder, provider_name)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    host = use_https(host_url)
    provider = NextcloudInstitutionsProvider(
        account=None, host=host.url,
        username=username, password=password)
    extended_data = {}
    extended_data[KEYNAME_NOTIFICATION_SECRET] = notification_secret
    return save_basic_storage_institutions_credentials_common(
        institution, storage_name, folder, provider_name, provider, extended_data=extended_data)

def save_s3compatinstitutions_credentials(institution, storage_name, host_url, access_key, secret_key, bucket, provider_name, server_side_encryption=False):
    host = host_url.rstrip('/').replace('https://', '').replace('http://', '')
    test_connection_result = test_s3compat_connection(
        host, access_key, secret_key, bucket)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    separator = '\t'
    provider = S3CompatInstitutionsProvider(
        account=None, host=host,
        username=access_key, password=secret_key, separator=separator)

    return save_basic_storage_institutions_credentials_common(
        institution, storage_name, bucket, provider_name, provider, separator, server_side_encryption=server_side_encryption)

def save_ociinstitutions_credentials(institution, storage_name, host_url, access_key, secret_key, bucket, provider_name):
    host = host_url.rstrip('/').replace('https://', '').replace('http://', '')
    test_connection_result = test_s3compatb3_connection(
        host, access_key, secret_key, bucket)
    if test_connection_result[1] != http_status.HTTP_200_OK:
        return test_connection_result

    separator = '\t'
    provider = OCIInstitutionsProvider(
        account=None, host=host,
        username=access_key, password=secret_key, separator=separator)

    return save_basic_storage_institutions_credentials_common(
        institution, storage_name, bucket, provider_name, provider, separator)

def get_credentials_common(institution, provider_name):
    clear_usermap_tmp(provider_name, institution)
    rdm_addon_option = get_rdm_addon_option(institution.id, provider_name,
                                            create=False)
    if not rdm_addon_option:
        return None
    exacc = rdm_addon_option.external_accounts.first()
    if not exacc:
        return None
    return rdm_addon_option, exacc

def get_nextcloudinstitutions_credentials(institution):
    provider_name = 'nextcloudinstitutions'
    res = get_credentials_common(institution, provider_name)
    if res:
        opt, exacc = res
        provider = NextcloudInstitutionsProvider(exacc)
        host = use_https(provider.host).host
        username = provider.username
        password = provider.password
        notification_secret = opt.extended.get(KEYNAME_NOTIFICATION_SECRET)
        folder = opt.extended.get(KEYNAME_BASE_FOLDER)
    else:
        host = ''
        username = ''
        password = ''
        notification_secret = None
        folder = None
    if not folder:
        folder = nextcloudinstitutions_settings.DEFAULT_BASE_FOLDER
    data = {}
    data[provider_name + '_host'] = host
    data[provider_name + '_username'] = username
    data[provider_name + '_password'] = password
    data[provider_name + '_notification_secret'] = notification_secret
    data[provider_name + '_folder'] = folder
    return data

def get_s3compatinstitutions_credentials(institution):
    provider_name = 's3compatinstitutions'
    res = get_credentials_common(institution, provider_name)
    if res:
        opt, exacc = res
        provider = S3CompatInstitutionsProvider(exacc)
        host = provider.host  # host:port
        access_key = provider.username
        secret_key = provider.password
        bucket = opt.extended.get(KEYNAME_BASE_FOLDER)
    else:
        host = ''
        access_key = ''
        secret_key = ''
        bucket = None
    if not bucket:
        bucket = s3compatinstitutions_settings.DEFAULT_BASE_BUCKET
    data = {}
    data[provider_name + '_endpoint_url'] = host
    data[provider_name + '_access_key'] = access_key
    data[provider_name + '_secret_key'] = secret_key
    data[provider_name + '_bucket'] = bucket
    return data

def get_ociinstitutions_credentials(institution):
    provider_name = 'ociinstitutions'
    res = get_credentials_common(institution, provider_name)
    if res:
        opt, exacc = res
        provider = OCIInstitutionsProvider(exacc)
        host = provider.host  # host:port
        access_key = provider.username
        secret_key = provider.password
        bucket = opt.extended.get(KEYNAME_BASE_FOLDER)
    else:
        host = ''
        access_key = ''
        secret_key = ''
        bucket = None
    if not bucket:
        bucket = ociinstitutions_settings.DEFAULT_BASE_BUCKET
    data = {}
    data[provider_name + '_endpoint_url'] = host
    data[provider_name + '_access_key'] = access_key
    data[provider_name + '_secret_key'] = secret_key
    data[provider_name + '_bucket'] = bucket
    return data

def extuser_exists(provider_name, post_params, extuser):
    # return "error reason", None means existence
    if provider_name == 'nextcloudinstitutions':
        provider_setting = nextcloudinstitutions_settings
        host_url = post_params.get(provider_name + '_host')
        username = post_params.get(provider_name + '_username')
        password = post_params.get(provider_name + '_password')
        # folder = post_params.get(provider_name + '_folder')
        try:
            host = use_https(host_url)
            client = owncloud.Client(host.url,
                                     verify_certs=provider_setting.USE_SSL)
            client.login(username, password)
            if client.user_exists(extuser):
                return None  # exist
            return 'not exist'
        except Exception as e:
            return str(e)
    else:  # unsupported
        return None  # ok

def get_usermap(provider_name, institution):
    rdm_addon_option = get_rdm_addon_option(institution.id, provider_name,
                                            create=False)
    if not rdm_addon_option:
        return None
    return rdm_addon_option.extended.get(KEYNAME_USERMAP)

def save_usermap_to_tmp(provider_name, institution, usermap):
    rdm_addon_option = get_rdm_addon_option(institution.id, provider_name)
    rdm_addon_option.extended[KEYNAME_USERMAP_TMP] = usermap
    rdm_addon_option.save()

def clear_usermap_tmp(provider_name, institution):
    rdm_addon_option = get_rdm_addon_option(institution.id, provider_name,
                                            create=False)
    if not rdm_addon_option:
        return
    new_usermap = rdm_addon_option.extended.get(KEYNAME_USERMAP_TMP)
    if new_usermap:
        del rdm_addon_option.extended[KEYNAME_USERMAP_TMP]
        rdm_addon_option.save()

def save_usermap_from_tmp(provider_name, institution):
    rdm_addon_option = get_rdm_addon_option(institution.id, provider_name)
    new_usermap = rdm_addon_option.extended.get(KEYNAME_USERMAP_TMP)
    if new_usermap:
        rdm_addon_option.extended[KEYNAME_USERMAP] = new_usermap
        del rdm_addon_option.extended[KEYNAME_USERMAP_TMP]
        rdm_addon_option.save()


def create_storage_info_template(field_name, value):
    """Create a standard storage information template."""
    return {'field_name': field_name, 'value': value}


def get_institution_addon_info(institution_id, provider_name):
    """Get institution addon option and external account."""
    rdm_addon_option = get_rdm_addon_option(institution_id, provider_name, create=False)
    external_account = rdm_addon_option.external_accounts.first()
    return rdm_addon_option, external_account


def get_osfstorage_info(waterbutler_settings_storage):
    """Get storage information for OSF storage."""
    return {
        'folder': create_storage_info_template('Folder', waterbutler_settings_storage.get('folder'))
    }


def get_s3_info(waterbutler_credentials_storage, waterbutler_settings_storage):
    """Get storage information for Amazon S3."""
    return {
        'access_key': create_storage_info_template('Access Key', waterbutler_credentials_storage.get('access_key')),
        'bucket': create_storage_info_template('Bucket', waterbutler_settings_storage.get('bucket')),
        'encrypt_uploads': create_storage_info_template(
            'Enable Server Side Encryption',
            waterbutler_settings_storage.get('encrypt_uploads', False)
        )
    }


def get_s3compat_info(waterbutler_credentials_storage, waterbutler_settings_storage):
    """Get storage information for S3 Compatible Storage."""
    return {
        'host': create_storage_info_template('Endpoint URL', waterbutler_credentials_storage.get('host')),
        'access_key': create_storage_info_template('Access Key', waterbutler_credentials_storage.get('access_key')),
        'bucket': create_storage_info_template('Bucket', waterbutler_settings_storage.get('bucket')),
        'encrypt_uploads': create_storage_info_template(
            'Enable Server Side Encryption',
            waterbutler_settings_storage.get('encrypt_uploads', False)
        )
    }


def get_s3compatinstitutions_info(institution, provider_name, region):
    """Get storage information for S3 Compatible Storage for Institutions."""
    rdm_addon_option, external_account = get_institution_addon_info(institution.id, provider_name)
    return {
        'host': create_storage_info_template('Endpoint URL', external_account.profile_url),
        'access_key': create_storage_info_template('Access Key', external_account.display_name),
        'bucket': create_storage_info_template('Bucket', rdm_addon_option.extended.get(KEYNAME_BASE_FOLDER)),
        'encrypt_uploads': create_storage_info_template(
            'Enable Server Side Encryption',
            region.waterbutler_settings.get('encrypt_uploads', False)
        )
    }


def get_ociinstitutions_info(institution, provider_name):
    """Get storage information for Oracle Cloud Infrastructure for Institutions."""
    rdm_addon_option, external_account = get_institution_addon_info(institution.id, provider_name)
    return {
        'host': create_storage_info_template('Endpoint URL', external_account.profile_url),
        'access_key': create_storage_info_template('Access Key', external_account.display_name),
        'bucket': create_storage_info_template('Bucket', rdm_addon_option.extended.get(KEYNAME_BASE_FOLDER))
    }


def get_nextcloudinstitutions_info(institution, provider_name):
    """Get storage information for Nextcloud for Institutions."""
    rdm_addon_option, external_account = get_institution_addon_info(institution.id, provider_name)
    return {
        'host': create_storage_info_template('Host URL', external_account.profile_url),
        'username': create_storage_info_template('Username', external_account.display_name),
        'folder': create_storage_info_template('Folder', rdm_addon_option.extended.get(KEYNAME_BASE_FOLDER)),
        'notification_secret': create_storage_info_template(
            'Connection common key from File Upload Notification App',
            rdm_addon_option.extended.get(KEYNAME_NOTIFICATION_SECRET)
        )
    }


def get_dropboxbusiness_info(institution, provider_name):
    """Get storage information for Dropbox Business."""
    rdm_addon_option, external_account = get_institution_addon_info(institution.id, provider_name)
    return {
        'authorized_by': create_storage_info_template('authorized_by', external_account.display_name)
    }


def get_institutional_storage_information(provider_name, region, institution):
    """Get current institutional storage information."""
    waterbutler_credentials_storage = region.waterbutler_credentials.get('storage', {})
    waterbutler_settings_storage = region.waterbutler_settings.get('storage', {})

    provider_handlers = {
        'osfstorage': lambda: get_osfstorage_info(waterbutler_settings_storage),
        's3': lambda: get_s3_info(waterbutler_credentials_storage, waterbutler_settings_storage),
        's3compat': lambda: get_s3compat_info(waterbutler_credentials_storage, waterbutler_settings_storage),
        's3compatinstitutions': lambda: get_s3compatinstitutions_info(institution, provider_name, region),
        'ociinstitutions': lambda: get_ociinstitutions_info(institution, provider_name),
        'nextcloudinstitutions': lambda: get_nextcloudinstitutions_info(institution, provider_name),
        'dropboxbusiness': lambda: get_dropboxbusiness_info(institution, provider_name)
    }

    return provider_handlers.get(provider_name, lambda: {})()
