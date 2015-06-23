from website.util import api_v2_url
import requests
import logging


"""
Temporarily provides functions that give access
to projects files. To be replaced with the standard
way files are accessed.
"""


def collect_files(pid):
    """ Return the contents of a projects files.
    :param pid: project id
    :return: list of file objects.
    """
    path = '/nodes/{}/files/'.format(pid)
    params = {'path': '/',
              'provider': 'osfstorage'}
    url = api_v2_url(path, params=params)
    response = requests.get(url).json()
    file_dicts = response.get('data', [])
    files = []
    for fd in file_dicts:
        file_data = {
            'name': fd['name'],
            'content': requests.get(fd['links']['self']).text,
            'size': fd['metadata']['size'],
            'pid': pid,
        }
        files.append(file_data)
    return files
