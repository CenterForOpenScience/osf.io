import os
import pytest
import urlparse
import requests

from website import settings as osf_settings
from api.base import settings as api_settings
from admin.base import settings as admin_settings


static_url = urlparse.urljoin(osf_settings.API_DOMAIN, '{}'.format(api_settings.STATIC_URL))
media_url = urlparse.urljoin(osf_settings.API_DOMAIN, '_{}'.format(api_settings.MEDIA_URL))
headers = {'X-ADMIN': admin_settings.ADMIN_API_SECRET}

@pytest.mark.django_db
class TestMediaCRUD:

    filename = 'Banner.svg'
    content = 'I dont care.'

    def test_upload_and_delete_media(self):
        file_path = os.path.join(api_settings.STATIC_FOLDER, self.filename)

        put = requests.put(media_url + self.filename, headers=headers, data=self.content)
        assert put.status_code == 204

        get = requests.get(static_url+self.filename)
        assert get.status_code == 200

        delete = requests.delete(media_url + self.filename, headers=headers)
        assert delete.status_code == 204

        assert not os.path.isfile(file_path)

    def test_upload_no_permissions(self):
        put = requests.put(media_url + self.filename, data=self.content)
        assert put.status_code == 401


    #TODO: Test replace media
    #TODO: Test more permissions
