from website import settings
import requests

class DiscourseException(Exception):
    pass

def request(method, path, data={}, user_name=None):
    params = {}
    params['api_key'] = settings.DISCOURSE_API_KEY
    params['api_username'] = user_name if user_name else settings.DISCOURSE_API_ADMIN_USER

    url = requests.compat.urljoin(settings.DISCOURSE_SERVER_URL, path)

    if method == 'get':
        params.update(data)
        result = requests.get(url, params=params)
    elif method == 'post':
        result = requests.post(url, data=data, params=params)
    elif method == 'put':
        result = requests.put(url, data=data, params=params)
    elif method == 'delete':
        result = requests.delete(url, data=data, params=params)
    else:
        raise DiscourseException('Unknown http method ' + method)

    if result.status_code < 200 or result.status_code > 299:
        raise DiscourseException('Discourse server responded to ' + method + ' request ' + result.url + ' with '
                                 + str(result.status_code) + ': ' + result.text[:500])

    return result.json() if result.text else None
