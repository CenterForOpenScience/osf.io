import pytest

from api.base.settings.defaults import API_BASE
from osf.models.licenses import NodeLicense

@pytest.mark.django_db
class TestLicenseList:

    def test_license_list(self, app):
        licenses = NodeLicense.objects.all()
        license_node = licenses[0]
        url_licenses = '/{}licenses/'.format(API_BASE)
        res_licenses = app.get(url_licenses)

        #test_license_list_success
        assert res_licenses.status_code == 200
        assert res_licenses.content_type == 'application/vnd.api+json'

        #test_license_list_count_correct
        total = res_licenses.json['links']['meta']['total']
        assert total == licenses.count()

        #test_license_list_name_filter
        url = '/{}licenses/?filter[name]={}'.format(API_BASE, license_node.name)
        res = app.get(url)
        data = res.json['data'][0]
        assert data['attributes']['name'] == license_node.name
        assert data['id'] == license_node._id

        #test_license_list_id_filter(self, licenses):
        url = '/{}licenses/?filter[id]={}'.format(API_BASE, license_node._id)
        res = app.get(url)
        data = res.json['data'][0]
        assert data['attributes']['name'] == license_node.name
        assert data['id'] == license_node._id
