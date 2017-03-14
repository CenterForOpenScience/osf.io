from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from osf_tests.factories import SubjectFactory, PreprintProviderFactory

class TestPreprintProviderField(ApiTestCase):
    def setUp(self):
        super(TestPreprintProviderField, self).setUp()
        self.preprint_provider = PreprintProviderFactory(about_link="https://agrixiv.wordpress.com/about/")
        self.preprint_provider.save()
        self.url = '/{}preprint_providers/{}/'.format(API_BASE, self.preprint_provider._id)

    def test_about_link_field(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['about_link'], 'https://agrixiv.wordpress.com/about/')
