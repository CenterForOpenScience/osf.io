# -*- coding: utf-8 -*-

import os
import json
import logging

from website import settings


logger = logging.getLogger(__name__)


def load_asset_paths():
    try:
        return json.load(open(settings.ASSET_HASH_PATH))
    except IOError:
        logger.error('No "webpack-assets.json" file found. You may need to run webpack.')
        raise


asset_paths = load_asset_paths()
base_static_path = '/static/public/js/'
def webpack_asset(path, asset_paths=asset_paths):
    """Mako filter that resolves a human-readable asset path to its name on disk
    (which may include the hash of the file).
    """
    key = path.replace(base_static_path, '').replace('.js', '')
    hash_path = asset_paths[key]
    return os.path.join(base_static_path, hash_path)
