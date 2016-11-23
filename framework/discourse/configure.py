from framework.discourse import common
from framework.discourse.common import DiscourseException, request

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

def configure_terms_of_service():
    """Perform search and replace on the TOS with the company_domain, company_short_name, company_full_name"""
    post_id = request('get', '/t/terms-of-service.json')['post_stream']['posts'][0]['id']
    post_content = request('get', '/posts/' + str(post_id) + '.json')['raw']

    post_content = post_content.replace('company_domain', settings.DISCOURSE_SERVER_SETTINGS['company_domain'])
    post_content = post_content.replace('company_short_name', settings.DISCOURSE_SERVER_SETTINGS['company_short_name'])
    post_content = post_content.replace('company_full_name', settings.DISCOURSE_SERVER_SETTINGS['company_full_name'])

    data = {}
    data['post[raw]'] = post_content
    request('put', '/posts/' + str(post_id), data)

if __name__ == '__main__':
    configure_server_settings()
    configure_embeddable_host()
    configure_intro_topic()
    configure_terms_of_service()
    print("Configuration complete!")
