# -*- coding: utf-8 -*-

from django.http import JsonResponse
from furl import furl
import httplib
import requests
import os
import owncloud

from addons.osfstorage.models import Region
from addons.owncloud import settings as owncloud_settings
from addons.nextcloud import settings as nextcloud_settings
from addons.s3 import utils as s3_utils
from addons.swift import utils as swift_utils
from addons.swift.provider import SwiftProvider
from website import settings as osf_settings

providers = None
enabled_providers_list = [
    's3', 'box', 'googledrive', 'osfstorage',
    'nextcloud', 'swift', 'owncloud', 's3compat'
]

def get_providers():
    provider_list = []
    for provider in osf_settings.ADDONS_AVAILABLE:
        if 'storage' in provider.categories and provider.short_name in enabled_providers_list:
            provider.icon_url_admin = \
                '/custom_storage_location/icon/{}/comicon.png'.format(provider.short_name)
            provider.modal_path = get_modal_path(provider.short_name)
            provider_list.append(provider)
    provider_list.sort(key=lambda x: x.full_name.lower())
    return provider_list

def get_addon_by_name(addon_short_name):
    """get Addon object from Short Name."""
    for addon in osf_settings.ADDONS_AVAILABLE:
        if addon.short_name == addon_short_name:
            return addon
    return None

def get_modal_path(short_name):
    base_path = os.path.join('rdm_custom_storage_location', 'providers')
    return os.path.join(base_path, '{}_modal.html'.format(short_name))

def test_s3_connection(access_key, secret_key):
    """Verifies new external account credentials and adds to user's list"""
    if not (access_key and secret_key):
        return JsonResponse({
            'message': 'All the fields above are required.'
        }, status=httplib.BAD_REQUEST)
    user_info = s3_utils.get_user_info(access_key, secret_key)
    if not user_info:
        return JsonResponse({
            'message': ('Unable to access account.\n'
                'Check to make sure that the above credentials are valid,'
                'and that they have permission to list buckets.')
        }, status=httplib.BAD_REQUEST)

    if not s3_utils.can_list(access_key, secret_key):
        return JsonResponse({
            'message': ('Unable to list buckets.\n'
                'Listing buckets is required permission that can be changed via IAM')
        }, status=httplib.BAD_REQUEST)
    s3_response = {
        'id': user_info.id,
        'display_name': user_info.display_name,
        'Owner': user_info.Owner,
    }

    return JsonResponse({
        'message': ('Credentials are valid'),
        'data': s3_response
    }, status=httplib.OK)

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

    host = furl()
    host.host = host_url.rstrip('/').replace('https://', '').replace('http://', '')
    host.scheme = 'https'

    try:
        oc = owncloud.Client(host.url, verify_certs=provider_setting.USE_SSL)
        oc.login(username, password)
        oc.logout()
    except requests.exceptions.ConnectionError:
        return JsonResponse({
            'message': ('Invalid {} server.').format(provider_name) + host.url
        }, status=httplib.BAD_REQUEST)
    except owncloud.owncloud.HTTPResponseError:
        return JsonResponse({
            'message': ('{} Login failed.').format(provider_name)
        }, status=httplib.UNAUTHORIZED)

    return JsonResponse({
        'message': ('Credentials are valid')
    }, status=httplib.OK)

def test_swift_connection(auth_version, auth_url, access_key, secret_key, tenant_name,
                          user_domain_name, project_domain_name, folder, container):
    """Verifies new external account credentials and adds to user's list"""
    if not (auth_version and auth_url and access_key and secret_key and tenant_name and folder and container):
        return JsonResponse({
            'message': 'All the fields above are required.'
        }, status=httplib.BAD_REQUEST)
    if auth_version == '3' and not user_domain_name:
        return JsonResponse({
            'message': 'The field `user_domain_name` is required when you choose identity V3.'
        }, status=httplib.BAD_REQUEST)
    if auth_version == '3' and not project_domain_name:
        return JsonResponse({
            'message': 'The field `project_domain_name` is required when you choose identity V3.'
        }, status=httplib.BAD_REQUEST)

    user_info = swift_utils.get_user_info(auth_version, auth_url, access_key,
                                    user_domain_name, secret_key, tenant_name,
                                    project_domain_name)

    if not user_info:
        return JsonResponse({
            'message': ('Unable to access account.\n'
                'Check to make sure that the above credentials are valid, '
                'and that they have permission to list containers.')
        }, status=httplib.BAD_REQUEST)

    if not swift_utils.can_list(auth_version, auth_url, access_key, user_domain_name,
                          secret_key, tenant_name, project_domain_name):
        return JsonResponse({
            'message': ('Unable to list containers.\n'
                'Listing containers is required permission.')
        }, status=httplib.BAD_REQUEST)

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
    return JsonResponse({
        'message': ('Credentials are valid'),
        'data': swift_response
    }, status=httplib.OK)

def save_s3_credentials(institution_id, storage_name, access_key, secret_key, bucket):
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

    default_region = Region.objects.first()
    Region.objects.update_or_create(
        _id=institution_id,
        defaults={
            'name': storage_name,
            'waterbutler_credentials': wb_credentials,
            'waterbutler_url': default_region.waterbutler_url,
            'mfr_url': default_region.mfr_url,
            'waterbutler_settings': wb_settings
        }
    )

    return JsonResponse({
        'message': ('Saved credentials successfully!!')
    }, status=httplib.OK)
