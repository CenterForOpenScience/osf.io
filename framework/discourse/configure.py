from . import *

from website import settings

import requests
from furl import furl
import time

def _get_embeddable_hosts():
    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/customize/embedding.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to getting embeddable hosts with '
                                 + str(result.status_code) + ' ' + result.text)
    return result.json()['embeddable_hosts']

def _config_embeddable_host():
    # just make sure one exists...
    embeddable_hosts = _get_embeddable_hosts()
    if len(embeddable_hosts):
        return

    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/embeddable_hosts')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    url.args['embeddable_host[host]'] = settings.DOMAIN

    result = requests.post(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to setting embeddable host with '
                                 + str(result.status_code) + ' ' + result.text)

def _get_customizations():
    url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/customize/css_html.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to getting customizations with '
                                 + str(result.status_code) + ' ' + result.text)

    return result.json()['site_customizations']

def _config_customization():
    old_ids = [c['id'] for c in _get_customizations()]
    for old_id in old_ids:
        url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/site_customizations/' + str(old_id))
        url.args['api_key'] = settings.DISCOURSE_API_KEY
        url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

        result = requests.delete(url.url)
        if result.status_code != 204:
            raise DiscourseException('Discourse server responded to deleting customization with '
                                     + str(result.status_code) + ' ' + result.text)

    for customization in settings.DISCOURSE_SERVER_CUSTOMIZATIONS:
        url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/site_customizations')
        url.args['api_key'] = settings.DISCOURSE_API_KEY
        url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

        for key, val in customization.items():
            url.args['site_customization[' + key + ']'] = val

        result = requests.post(url.url)
        if result.status_code != 201:
            raise DiscourseException('Discourse server responded to setting customization with '
                                     + str(result.status_code) + ' ' + result.text)
        time.sleep(0.1)

def configure_server_settings():
    for key, val in settings.DISCOURSE_SERVER_SETTINGS.items():
        url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/site_settings/' + key)
        url.args[key] = val
        url.args['api_key'] = settings.DISCOURSE_API_KEY
        url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

        result = requests.put(url.url)
        if result.status_code != 200:
            raise DiscourseException('Discourse server responded to setting request with '
                                     + str(result.status_code) + ' ' + result.text)
        time.sleep(0.1)
    _config_embeddable_host()
    _config_customization()

if __name__ == '__main__':
    configure_server_settings()
