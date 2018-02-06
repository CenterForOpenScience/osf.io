# -*- coding: utf-8 -*-
import os
import requests
from flask import send_from_directory, Response, stream_with_context

from website.settings import EXTERNAL_EMBER_APPS, PROXY_EMBER_APPS, APP_PATH

quickfiles_dir = os.path.abspath(os.path.join(APP_PATH, EXTERNAL_EMBER_APPS['quickfiles']['path']))

def use_ember_app(**kwargs):
    if PROXY_EMBER_APPS:
        resp = requests.get(EXTERNAL_EMBER_APPS['quickfiles']['server'], stream=True)
        return Response(stream_with_context(resp.iter_content()), resp.status_code)
    return send_from_directory(quickfiles_dir, 'index.html')
