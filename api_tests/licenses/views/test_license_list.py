from nose.tools import *  # flake8: noqa
import functools

from tests.base import ApiTestCase
from website.project.licenses import NodeLicense
from website.project.licenses import ensure_licenses
from api.base.settings.defaults import API_BASE

ensure_licenses = functools.partial(ensure_licenses, warn=False)


class TestLicenseList(ApiTestCase):
    def setUp(self):
        super(TestLicenseList, self).setUp()
        ensure_licenses()
        self.licenses = NodeLicense.find()

    def test_license_list_success(self):
        url = '/{}licenses/'.format(API_BASE)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_license_list_count_correct(self):
        url = '/{}licenses/'.format(API_BASE)
        res = self.app.get(url)
        total = res.json['links']['meta']['total']
        assert_equal(total, self.licenses.count())

    def test_license_list_name_filter(self):
        license = self.licenses[0]
        name = license.name
        url = '/{}licenses/?filter[name]={}'.format(API_BASE, name)
        res = self.app.get(url)
        data = res.json['data'][0]
        assert_equal(data['attributes']['name'], name)
        assert_equal(data['id'], license._id)

    def test_license_list_id_filter(self):
        license = self.licenses[0]
        id = license._id
        url = '/{}licenses/?filter[id]={}'.format(API_BASE, id)
        res = self.app.get(url)
        data = res.json['data'][0]
        assert_equal(data['attributes']['name'], license.name)
        assert_equal(data['id'], id)