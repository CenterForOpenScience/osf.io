# -*- coding: utf-8 -*-

import json
import os
from website import settings as osf_settings

addons = None
enabled_addons_list = [
    's3', 'box', 'googledrive', 'osfstorage',
    'nextcloud', 'swift', 'owncloud', 's3compat'
]


def get_provider_short_name(settings):
    if 'storage' in settings and 'provider' in settings['storage']:
        return settings['storage']['provider']
    return 'osfstorage'

def load_addons_info():
    data = None
    with open(osf_settings.APP_PATH + '/addons.json') as f:
        data = json.load(f)
    return data

def get_providers():
    provider_list = []
    for provider in osf_settings.ADDONS_AVAILABLE:
        if 'storage' in provider.categories and provider.short_name in enabled_addons_list:
            provider.icon_url_admin = \
                '/addons/icon_ignore_config/{}/comicon.png'.format(provider.short_name)
            provider.modal_path = get_modal_path(provider.short_name)
            provider_list.append(provider)
    return provider_list

def get_modal_path(short_name):
    base_path = os.path.join('rdm_custom_storage_location', 'providers')
    return os.path.join(base_path, '{}_modal.html'.format(short_name))
