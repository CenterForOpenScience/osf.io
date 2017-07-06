import pytest

from api.base.settings.defaults import API_BASE
from osf.models.licenses import NodeLicense

@pytest.mark.django_db
class TestLicenseList:

    @pytest.fixture()
    def licenses(self):
        return NodeLicense.find()

    @pytest.fixture()
    def url_licenses(self):
        return '/{}licenses/'.format(API_BASE)

    @pytest.fixture()
    def res_licenses(self, app, url_licenses):
        return app.get(url_licenses)


    def test_license_list(self, licenses, app, url_licenses, res_licenses):
        #test_license_list_success
        assert res_licenses.status_code == 200
        assert res_licenses.content_type == 'application/vnd.api+json'

        #test_license_list_count_correct
        total = res_licenses.json['links']['meta']['total']
        assert total == licenses.count()

        #test_license_list_name_filter
        license = licenses[0]
        url = '/{}licenses/?filter[name]={}'.format(API_BASE, license.name)
        res = app.get(url)
        data = res.json['data'][0]
        assert data['attributes']['name'] == license.name
        assert data['id'] == license._id

        #test_license_list_id_filter(self, licenses):
        url = '/{}licenses/?filter[id]={}'.format(API_BASE, license._id)
        res = app.get(url)
        data = res.json['data'][0]
        assert data['attributes']['name'] == license.name
        assert data['id'] == license._id
