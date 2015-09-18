# -*- coding: utf-8 -*-

import os
import json
import logging

from website import settings


logger = logging.getLogger(__name__)


def load_asset_paths():
    if settings.DEBUG_MODE:
        logger.warn('Skipping load of "webpack-assets.json" in DEBUG_MODE.')
        return
    asset_paths = None
    try:
        with open(settings.ASSET_HASH_PATH) as fp:
            asset_paths = json.load(fp)
    except IOError:
        logger.error('No "webpack-assets.json" file found. You may need to run webpack.')
        pass
    return asset_paths


asset_paths = load_asset_paths()
base_static_path = '/static/public/js/'
def webpack_asset(path, asset_paths=asset_paths, debug=settings.DEBUG_MODE):
    """Mako filter that resolves a human-readable asset path to its name on disk
    (which may include the hash of the file).
    """
    if not asset_paths:
        logger.warn('webpack-assets.json has not yet been generated. Falling back to non-cache-busted assets')
        return path
    if not debug:
        key = path.replace(base_static_path, '').replace('.js', '')
        hash_path = asset_paths[key]
        return os.path.join(base_static_path, hash_path)
    else:  # We don't cachebust in debug mode, so just return unmodified path
        return path


def resolve_addon_path(addon_config, file_name):
    """Check for addon asset in source directory (e.g. website/addons/dropbox/static');
    if file is found, return path to webpack-built asset.

    :param AddonConfig config: Addon config object
    :param str file_name: Asset file name (e.g. "files.js")
    """
    source_path = os.path.join(
        settings.ADDON_PATH,
        addon_config.short_name,
        'static',
        file_name,
    )
    if os.path.exists(source_path):
        return os.path.join(
            '/',
            'static',
            'public',
            'js',
            addon_config.short_name,
            file_name,
        )
    return None
