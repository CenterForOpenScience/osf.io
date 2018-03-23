# -*- coding: utf-8 -*-
import os
import json
import requests
from flask import send_from_directory, Response, stream_with_context

from framework.sessions import session
from website.settings import EXTERNAL_EMBER_APPS, PROXY_EMBER_APPS, EXTERNAL_EMBER_SERVER_TIMEOUT

ember_osf_web_dir = os.path.abspath(os.path.join(os.getcwd(), EXTERNAL_EMBER_APPS['ember_osf_web']['path']))

routes = [
    '/quickfiles/',
    '/<uid>/quickfiles/'
]

def use_ember_app(**kwargs):
    if PROXY_EMBER_APPS:
        resp = requests.get(EXTERNAL_EMBER_APPS['ember_osf_web']['server'], stream=True, timeout=EXTERNAL_EMBER_SERVER_TIMEOUT)
        resp = Response(stream_with_context(resp.iter_content()), resp.status_code)
    else:
        resp = send_from_directory(ember_osf_web_dir, 'index.html')
    resp.set_cookie('status', json.dumps(session.data.get('status')))
    return resp
