from __future__ import absolute_import

import urlparse
import requests
from website import settings as osf_settings
from api.base import settings as api_settings
from admin.base import settings as admin_settings

from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

@deconstructible
class ApiFileStorage(Storage):
    static_url = urlparse.urljoin(osf_settings.API_DOMAIN, '{}'.format(api_settings.STATIC_URL))
    media_url = urlparse.urljoin(osf_settings.API_DOMAIN, '_{}'.format(api_settings.MEDIA_URL))
    headers = {'X-ADMIN': admin_settings.ADMIN_API_SECRET}

    def _open(self, name, mode='rb'):
        resp = requests.get(self.url(name))
        return resp

    def _save(self, name, content):
        requests.put(self.media_url + name, headers=self.headers, data=content)
        # TODO: Add error handling here

        return name  # TODO: change to the response name

    def delete(self, name):
        requests.delete(self.static_url + name, headers=self.headers)

    def exists(self, name):
        resp = self._open(name)  # TODO: Is there a better way to do this
        if resp.status_code == 404:
            return False
        elif resp.status_code == 200:
            return True
        else:
            raise Exception

    def url(self, name):
        return self.static_url + name

    def get_available_name(self, name, max_length=None):
        # Overwrite old files instead of renaming them
        if self.exists(name):
            self.delete(name)
        return name
