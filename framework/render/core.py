# -*- coding: utf-8 -*-
import os

import mfr
from mfr.ext import ALL_HANDLERS

def init_mfr(app):
    """Register all available FileHandlers and collect each
    plugin's static assets to the app's static path.
    """
    # Available file handlers
    mfr.register_filehandlers(ALL_HANDLERS)

    # Update mfr config with static path and url
    mfr.config.update({
        # Base URL for static files
        'ASSETS_URL': os.path.join(app.static_url_path, 'mfr'),
        # Where to save static files
        'ASSETS_FOLDER': os.path.join(app.static_folder, 'mfr'),
    })
    mfr.collect_static(dest=mfr.config['ASSETS_FOLDER'])
