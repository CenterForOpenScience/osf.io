from django.core.files.storage import FileSystemStorage
from django.utils.encoding import filepath_to_uri
from storages.backends.gcloud import GoogleCloudStorage
from future.moves.urllib.parse import urljoin

from website.settings import DOMAIN


class DevFileSystemStorage(FileSystemStorage):

    def url(self, name):
        if self.base_url is None:
            raise ValueError('This file is not accessible via a URL.')
        url = filepath_to_uri(name)
        if url is not None:
            url = url.lstrip('/')
        url = urljoin(DOMAIN, url)
        return urljoin(self.base_url, url)

class RequestlessURLGoogleCloudStorage(GoogleCloudStorage):
    def url(self, name, validate=False):
        if validate:
            return super(RequestlessURLGoogleCloudStorage, self).url(name)
        # This assumes that any name given will be a valid one (cached on the GoogleCloudFile object),
        # and passes potential 404's to the front-end. It avoids making a request to GCS at every serialization.
        return 'https://storage.googleapis.com/{}/{}'.format(self.bucket.name, name)
