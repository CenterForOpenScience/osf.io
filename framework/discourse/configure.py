from .common import *

from website import settings
import time

def _get_embeddable_hosts():
    result = request('get', '/admin/customize/embedding.json')
    return result['embeddable_hosts']

def configure_embeddable_host():
    # just make sure one exists...
    embeddable_hosts = _get_embeddable_hosts()
    if len(embeddable_hosts):
        return

    data = {}
    data['embeddable_host[host]'] = settings.DOMAIN
    return request('post', '/admin/embeddable_hosts', data)

def _get_customizations():
    result = request('get', '/admin/customize/css_html.json')
    return result['site_customizations']

def configure_customizations():
    old_ids = [c['id'] for c in _get_customizations()]
    for old_id in old_ids:
        request('delete', '/admin/site_customizations/' + str(old_id))

    for customization in settings.DISCOURSE_SERVER_CUSTOMIZATIONS:
        data = {}
        for key, val in customization.items():
            data['site_customization[' + key + ']'] = val
        request('post', '/admin/site_customizations', data)

        time.sleep(0.1)

def configure_server_settings():
    for key, val in settings.DISCOURSE_SERVER_SETTINGS.items():
        data = {}
        data[key] = val
        request('put', '/admin/site_settings/' + key, data)

        time.sleep(0.1)

if __name__ == '__main__':
    configure_server_settings()
    configure_customizations()
    configure_embeddable_host()
