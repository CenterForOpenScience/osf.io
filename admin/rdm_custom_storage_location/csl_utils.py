# -*- coding: utf-8 -*-

import json
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

def get_addons():
    addon_list = []
    for addon in osf_settings.ADDONS_AVAILABLE:
        if 'storage' in addon.categories and addon.short_name in enabled_addons_list:
            addon.icon_url_admin = \
                '/addons/icon_ignore_config/{}/comicon.png'.format(addon.short_name)
            addon_list.append(addon)
    return addon_list
