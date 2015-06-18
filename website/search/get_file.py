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
    api_url = API_DOMAIN + 'v2/nodes/{}/files/?path=%2F&provider=osfstorage'.format(pid)
    return api_url


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
