from framework.discourse import common

from website import settings
import time

def _get_embeddable_hosts():
    """Return the embeddable host list from the Discourse configuration
    :return list: list of embeddable hosts configured for Discourse to be used with
    """
    result = request('get', '/admin/customize/embedding.json')
    return result['embeddable_hosts']

def configure_embeddable_host():
    """Make sure Discourse is configured to have an embeddable host (it should be settings.DOMAIN)"""
    embeddable_hosts = _get_embeddable_hosts()
    if len(embeddable_hosts):
        return

    data = {}
    data['embeddable_host[host]'] = settings.DOMAIN
    request('post', '/admin/embeddable_hosts', data)

def configure_server_settings():
    """Sets Discourse site settings (available in the admin panel) from settings.DISCOURSE_SERVER_SETTINGS"""
    for key, val in settings.DISCOURSE_SERVER_SETTINGS.items():
        data = {}
        data[key] = val
        request('put', '/admin/site_settings/' + key, data)

        time.sleep(0.1)

def configure_intro_topic():
    """Sets Discourse intro topic text to be settings.DISCOURSE_WELCOME_TOPIC"""
    post_id = request('get', '/t/welcome-to-discourse.json')['post_stream']['posts'][0]['id']

    data = {}
    data['post[raw]'] = settings.DISCOURSE_WELCOME_TOPIC
    request('put', '/posts/' + str(post_id), data)

if __name__ == '__main__':
    configure_server_settings()
    configure_embeddable_host()
    configure_intro_topic()
    print("Configuration complete!")
