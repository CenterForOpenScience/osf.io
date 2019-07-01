# -*- coding: utf-8 -*-

import httplib
import os
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
