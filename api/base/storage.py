from django.core.files.storage import FileSystemStorage
from django.utils.encoding import filepath_to_uri
from urlparse import urljoin

from website.settings import DOMAIN


class DevFileSystemStorage(FileSystemStorage):

    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        url = filepath_to_uri(name)
        if url is not None:
            url = url.lstrip('/')
        url = urljoin(DOMAIN, url)
        return urljoin(self.base_url, url)
