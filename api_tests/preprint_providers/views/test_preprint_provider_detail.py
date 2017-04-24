from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from osf_tests.factories import PreprintProviderFactory


class TestPreprintProviderExists(ApiTestCase):

    # Regression for https://openscience.atlassian.net/browse/OSF-7621

    def setUp(self):
        super(TestPreprintProviderExists, self).setUp()
        self.preprint_provider = PreprintProviderFactory()
        self.fake_url = '/{}preprint_providers/fake/'.format(API_BASE)
        self.provider_url = '/{}preprint_providers/{}/'.format(API_BASE, self.preprint_provider._id)

    def test_preprint_provider(self):
        detail_res = self.app.get(self.provider_url)
        assert_equals(detail_res.status_code, 200)

        licenses_res = self.app.get('{}licenses/'.format(self.provider_url))
        assert_equals(licenses_res.status_code, 200)

        preprints_res = self.app.get('{}preprints/'.format(self.provider_url))
        assert_equals(preprints_res.status_code, 200)

        taxonomies_res = self.app.get('{}taxonomies/'.format(self.provider_url))
        assert_equals(taxonomies_res.status_code, 200)

    def test_preprint_provider_does_not_exist_returns_404(self):
        detail_res = self.app.get(self.fake_url, expect_errors=True)
        assert_equals(detail_res.status_code, 404)

        licenses_res = self.app.get('{}licenses/'.format(self.fake_url), expect_errors=True)
        assert_equals(licenses_res.status_code, 404)

        preprints_res = self.app.get('{}preprints/'.format(self.fake_url), expect_errors=True)
        assert_equals(preprints_res.status_code, 404)

        taxonomies_res = self.app.get('{}taxonomies/'.format(self.fake_url), expect_errors=True)
        assert_equals(taxonomies_res.status_code, 404)
