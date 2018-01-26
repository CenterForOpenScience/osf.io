from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from osf.models.licenses import NodeLicense
from osf_tests.factories import PreprintProviderFactory


class TestPreprintProviderLicenses(ApiTestCase):
    def setUp(self):
        super(TestPreprintProviderLicenses, self).setUp()
        self.provider = PreprintProviderFactory()
        self.licenses = NodeLicense.objects.all()
        self.license1 = self.licenses[0]
        self.license2 = self.licenses[1]
        self.license3 = self.licenses[2]
        self.url = '/{}preprint_providers/{}/licenses/'.format(
            API_BASE, self.provider._id)

    def test_preprint_provider_has_no_acceptable_licenses_and_no_default(self):
        self.provider.licenses_acceptable = []
        self.provider.default_license = None
        self.provider.save()
        res = self.app.get(self.url)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], len(self.licenses))

    def test_preprint_provider_has_a_default_license_but_no_acceptable_licenses(
            self):
        self.provider.licenses_acceptable = []
        self.provider.default_license = self.license2
        self.provider.save()
        res = self.app.get(self.url)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], len(self.licenses))

        assert_equal(self.license2._id, res.json['data'][0]['id'])

    def test_prerint_provider_has_acceptable_licenses_but_no_default(self):
        self.provider.licenses_acceptable.add(self.license1, self.license2)
        self.provider.default_license = None
        self.provider.save()
        res = self.app.get(self.url)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)

        license_ids = [item['id'] for item in res.json['data']]
        assert_in(self.license1._id, license_ids)
        assert_in(self.license2._id, license_ids)
        assert_not_in(self.license3._id, license_ids)

    def test_preprint_provider_has_both_acceptable_and_default_licenses(self):
        self.provider.licenses_acceptable.add(self.license1, self.license3)
        self.provider.default_license = self.license3
        self.provider.save()
        res = self.app.get(self.url)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['links']['meta']['total'], 2)

        license_ids = [item['id'] for item in res.json['data']]
        assert_in(self.license1._id, license_ids)
        assert_in(self.license3._id, license_ids)
        assert_not_in(self.license2._id, license_ids)

        assert_equal(self.license3._id, license_ids[0])
