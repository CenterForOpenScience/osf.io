from website import settings
import requests
from simplejson.scanner import JSONDecodeError

class DiscourseException(Exception):
    pass

def request(method, path, data={}, user_name=None):
    params = {}
    params['api_key'] = settings.DISCOURSE_API_KEY
    params['api_username'] = user_name if user_name else settings.DISCOURSE_API_ADMIN_USER

    url = requests.compat.urljoin(settings.DISCOURSE_SERVER_URL, path)
    result = getattr(requests, method)(url, data=data, params=params)

    if result.status_code < 200 or result.status_code > 299:
        raise DiscourseException('Discourse server responded to ' + method + ' request ' + result.url + ' with '
                                 + ' post data ' + str(data) + ' with result code '
                                 + str(result.status_code) + ': ' + result.text[:500])

    try:
        return result.json()
    except JSONDecodeError:
        return None
