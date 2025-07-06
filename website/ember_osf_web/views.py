import os
import json
from website import settings
from framework.status import pop_status_messages

from website.settings import EXTERNAL_EMBER_APPS

def get_primary_app_config():
    from website.settings import PRIMARY_WEB_APP
    return EXTERNAL_EMBER_APPS.get(PRIMARY_WEB_APP, {})

def get_primary_app_dir():
    app_config = get_primary_app_config()
    if 'path' in app_config:
        return os.path.abspath(os.path.join(os.getcwd(), app_config['path']))
    return None

routes = [
    '/institutions/',
]

def use_ember_app(**kwargs):
    from rest_framework import status as http_status
    from framework.exceptions import HTTPError
    from website.views import stream_emberapp

    app_config = get_primary_app_config()
    if not app_config:
        raise HTTPError(
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            data={'message': 'Primary web app not configured'}
        )

    resp = stream_emberapp(app_config['server'], get_primary_app_dir())
    messages = pop_status_messages()
    if messages:
        try:
            status = [{'id': stat[5] if stat[5] else stat[0], 'class': stat[2], 'jumbo': stat[1], 'dismiss': stat[3], 'extra': stat[6]} for stat in messages]
            resp.set_cookie(settings.COOKIE_NAME + '_status', json.dumps(status))
        except IndexError:
            # Ignoring the error as it will only occur when statuses were created prior to merging the changes that add
            # extra and id, (patch to prevent breaking the app meanwhile)
            pass
    return resp
