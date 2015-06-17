from website.settings import API_DOMAIN
import requests

"""
Temporarily provides functions that give access
to projects files. To be replaced with the standard
way files are accessed.
"""


def build_api_call(pid):
    """ Get a url to a project's files.
    :param pid: project id
    :return: url to project's files

    Utilizes api v2.
    """

    path = ['v2']
    path.append('nodes')
    path.append(pid)
    path.append('files')
    end_part = '?path=%2F&provider=osfstorage'
    url = API_DOMAIN + '/'.join(path) + end_part
    return url


def get_files_for(pid):
    """ Return the contents of a projects files.
    :param pid: project id
    :return: list of unicode strings.
    """
    files_url = build_api_call(pid)
    files = requests.get(files_url).json().get('data', [])
    file_contents = []
    for f in files:
        download_url = f['links']['self']
        contents = requests.get(download_url).text
        file_contents.append(contents)
    return file_contents
