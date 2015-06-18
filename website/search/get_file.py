from website.settings import API_DOMAIN
from pprint import pprint
import requests


"""
Temporarily provides functions that give access
to projects files. To be replaced with the standard
way files are accessed.
"""


class File(object):
    def __init__(self, name, download_link, pid):
        self.name = name
        self.download_link = download_link
        self.pid = pid

    @classmethod
    def from_dict(cls, d, pid):
        name = d['name']
        download_link = d['links']['self']
        new_file = File(name, download_link, pid)
        return new_file

    @property
    def extension(self):
        ext_start = self.name.rfind('.')
        return self.name[ext_start:] if ext_start >= 0 else None

    @property
    def contents(self):
        content = requests.get(self.download_link)
        return content.text if content else None

    def __repr__(self):
        s = u'<{} {} from {}>'.format(self.__class__, self.name, self.pid)
        s = s.encode('ascii', 'replace')
        return s


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
    :return: list of file objects.
    """

    url = build_api_call(pid)
    response = requests.get(url).json()

    # print("RESPONSE:")
    # pprint(response)

    file_dicts = response.get('data', [])

    # print('FILES_DICTS:')
    # pprint(file_dicts)

    files = []
    for fd in file_dicts:
        files.append(File.from_dict(fd, pid))

    # print('FILES:')
    # pprint(files)

    file_contents = []
    return file_contents
