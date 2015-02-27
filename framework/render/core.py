# -*- coding: utf-8 -*-
import os
import time

import mfr
from mfr.ext import ALL_HANDLERS

import requests

from framework.render.exceptions import error_message_or_exception

from website import settings


def init_mfr(app):
    """Register all available FileHandlers and collect each
    plugin's static assets to the app's static path.
    """
    # Available file handlers
    mfr.register_filehandlers(ALL_HANDLERS)

    # Update mfr config with static path and url
    mfr.config.update({
        # Base URL for static files
        'ASSETS_URL': os.path.join(app.static_url_path, 'public', 'mfr'),
        # Where to save static files
        'ASSETS_FOLDER': os.path.join(app.static_folder, 'public', 'mfr'),
    })
    mfr.collect_static(dest=mfr.config['ASSETS_FOLDER'])


def render_is_done_or_happening(cache_path, temp_path):
    # if the cached file exists do nothing
    if os.path.isfile(cache_path):
        return True

    if os.path.isfile(temp_path):
        if time.time() - os.path.getmtime(temp_path) > settings.MFR_TIMEOUT:
            # If the temp path has not been modified since the timeout
            # seconds assume the task failed, remove the file and
            # start over
            os.remove(temp_path)
            return False
        # Otherwise the task is happening somewhere else
        return True

    # If none of the above go ahead and start
    return False


def save_to_file_or_error(download_url, dest_path):
    with open(dest_path, 'wb') as temp_file:
        response = requests.get(download_url, stream=True)
        if response.ok:
            for block in response.iter_content(1024):  # 1kb
                temp_file.write(block)
            return response
        temp_file.write(
            error_message_or_exception(
                response.status_code,
                dest_path=dest_path,
                download_url=download_url,
            )
        )
