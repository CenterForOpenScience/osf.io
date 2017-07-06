import pytest
import functools

from api.base.settings.defaults import API_BASE
from osf.models.licenses import NodeLicense

@pytest.mark.django_db
class TestLicenseDetail:
    @pytest.fixture()
    def license(self):
        return NodeLicense.find()[0]

    @pytest.fixture()
    def url_license(self, license):
        return '/{}licenses/{}/'.format(API_BASE, license._id)

    @pytest.fixture()
    def res_license(self, app, url_license):
        return app.get(url_license)

    @pytest.fixture()
    def data_license(self, res_license):
        return res_license.json['data']

    def test_license_detail(self, license, res_license, data_license):

        #test_license_detail_success(self, res_license):
        assert res_license.status_code == 200
        assert res_license.content_type == 'application/vnd.api+json'

        #test_license_top_level(self, license, data_license):
        assert data_license['type'] == 'licenses'
        assert data_license['id'] == license._id

        #test_license_name(self, data_license, license):
        assert data_license['attributes']['name'] == license.name

        #test_license_text(self, data_license, license):
        assert data_license['attributes']['text'] == license.text
