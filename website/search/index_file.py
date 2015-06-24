from website.util import api_v2_url
import requests


def collect_files(pid):
    """ Return the contents of a projects files.
    :param pid: project id
q    :return: list of file objects.
 qq   """
    path = '/nodes/{}/files/'.format(pid)
    params = {'path': '/',
              'provider': 'osfstorage'}
    url = api_v2_url(path, params=params)
    response = requests.get(url).json()
    file_dicts = response.get('data', [])
    for fd in file_dicts:
        file_data = {
            'name': fd['name'],
            'content': requests.get(fd['links']['self']).text,
            'size': fd['metadata']['size'],
            'pid': pid,
        }
        yield file_data
