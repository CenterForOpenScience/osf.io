from website.settings import API_DOMAIN
import requests


"""
Temporarily provides functions that give access
to projects files. To be replaced with the standard
way files are accessed.
"""

PROJECT_FILES_URL = 'v2/nodes/{}/files/?path=%2F&provider=osfstorage'

class File(object):
    MAX_SIZE = 1000
    INDEXED_EXTENSIONS = [
        '.txt',
        '.md',
        '.py',
    ]

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
    def content(self):
        if self.extension not in File.INDEXED_EXTENSIONS:
            return ''

        c = requests.get(self.download_link)
        size = min(File.MAX_SIZE, len(c.text))
        return c.text[:size] if c else ''

    @property
    def dict(self):
        return {
            'filename': self.name,
            'pid': self.pid,
            'content': self.content,
        }

    def __repr__(self):
        s = u'<{} {} from {}>'.format(self.__class__, self.name, self.pid)
        s = s.encode('ascii', 'replace')
        return s


def collect_files(pid):
    """ Return the contents of a projects files.
    :param pid: project id
    :return: list of file objects.
    """
    url = API_DOMAIN + PROJECT_FILES_URL.format(pid)
    response = requests.get(url).json()
    file_dicts = response.get('data', [])
    files = []
    for fd in file_dicts:
        files.append(File.from_dict(fd, pid))
    return files
