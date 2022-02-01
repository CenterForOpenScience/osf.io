# -*- coding: utf-8 -*-
import os
import json
import logging

from django.template.defaultfilters import register
from website.util.paths import webpack_asset as _webpack_asset
from admin.base import settings as admin_settings

logger = logging.getLogger(__name__)

@register.filter(is_safe=True)
def render_user_settings_template(addon):
    tmpl = addon['user_settings_template']
    return tmpl.render(**addon)

def load_asset_paths():
    if admin_settings.DEBUG:
        logger.warn('Skipping load of "webpack-assets.json" in DEBUG_MODE.')
        return
    asset_paths = None
    try:
        with open(os.path.join(admin_settings.BASE_DIR, 'webpack-assets.json')) as fp:
            asset_paths = json.load(fp)
    except IOError:
        logger.error('No "webpack-assets.json" file found. You may need to run webpack.')
        pass
    return asset_paths

@register.filter(is_safe=True)
def webpack_asset(path):
    return _webpack_asset(path, asset_paths=load_asset_paths())

@register.filter
def external_account_id(account):
    return account['_id']
