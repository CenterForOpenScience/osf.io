import pytest
import functools

from api.base.settings.defaults import API_BASE
from osf.models.licenses import NodeLicense

@pytest.mark.django_db
class TestLicenseDetail:

    def test_license_detail(self, app):
        license_node = NodeLicense.objects.first()
        url_license = '/{}licenses/{}/'.format(API_BASE, license_node._id)
        res_license = app.get(url_license)
        data_license = res_license.json['data']

        #test_license_detail_success(self, res_license):
        assert res_license.status_code == 200
        assert res_license.content_type == 'application/vnd.api+json'

        #test_license_top_level(self, license, data_license):
        assert data_license['type'] == 'licenses'
        assert data_license['id'] == license_node._id

        #test_license_name(self, data_license, license):
        assert data_license['attributes']['name'] == license_node.name

        #test_license_text(self, data_license, license):
        assert data_license['attributes']['text'] == license_node.text
