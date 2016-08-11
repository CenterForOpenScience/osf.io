from nose.tools import *  # flake8: noqa
import functools

from tests.base import ApiTestCase
from website.project.licenses import NodeLicense
from website.project.licenses import ensure_licenses
from api.base.settings.defaults import API_BASE

ensure_licenses = functools.partial(ensure_licenses, warn=False)


class TestLicenseDetail(ApiTestCase):
    def setUp(self):
        super(TestLicenseDetail, self).setUp()
        ensure_licenses()
        self.license = NodeLicense.find()[0]
        self.url = '/{}licenses/{}/'.format(API_BASE, self.license._id)
        self.res = self.app.get(self.url)
        self.data = self.res.json['data']

    def test_license_detail_success(self):
        assert_equal(self.res.status_code, 200)
        assert_equal(self.res.content_type, 'application/vnd.api+json')

    def test_license_top_level(self):
        assert_equal(self.data['type'], 'licenses')
        assert_equal(self.data['id'], self.license._id)

    def test_license_name(self):
        assert_equal(self.data['attributes']['name'], self.license.name)

    def test_license_text(self):
        assert_equal(self.data['attributes']['text'], self.license.text)