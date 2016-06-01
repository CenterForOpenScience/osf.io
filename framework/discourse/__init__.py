from framework.sessions import session

import requests
from furl import furl

from website import settings

class DiscourseException(Exception):
    pass

def get_username():
    if 'auth_discourse_username' in session.data:
        return session.data['auth_discourse_username']

    if 'auth_user_id' in session.data:
        user_id = session.data['auth_user_id']
    else:
        raise DiscourseException('No authenticated user to query discourse for')

    url = furl(settings.DISCOURSE_SERVER_URL).join('/users/by-external/' + user_id + '.json')
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

    result = requests.get(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to user request with ' + str(result.status_code))

    username = result.json()['user']['username']
    session.data['auth_discourse_username'] = username

    return username

def logout():
    username = get_username()

    url = furl(settings.DISCOURSE_SERVER_URL).join('/session/' + username)
    url.args['api_key'] = settings.DISCOURSE_API_KEY
    url.args['api_username'] = username

    result = requests.delete(url.url)
    if result.status_code != 200:
        raise DiscourseException('Discourse server responded to logout request with ' + str(result.status_code))

def configure_server_settings():
    discourse_settings = settings.DISCOURSE_SERVER_SETTINGS
    for key, val in settings.DISCOURSE_SERVER_SETTINGS.items():
        url = furl(settings.DISCOURSE_SERVER_URL).join('/admin/site_settings/' + key)
        url.args[key] = val
        url.args['api_key'] = settings.DISCOURSE_API_KEY
        url.args['api_username'] = settings.DISCOURSE_API_ADMIN_USER

        result = requests.put(url.url)
        if result.status_code != 200:
            raise DiscourseException('Discourse server responded to setting request with ' + str(result.status_code))
