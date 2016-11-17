from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase

class TestAddonsList(ApiTestCase):

    def setUp(self):
        super(TestAddonsList, self).setUp()
        self.url = '/{}addons/'.format(API_BASE)

    def test_filter_by_category(self):
        storage_url = '{}?filter[categories]=storage'.format(self.url)
        citations_url = '{}?filter[categories]=citations'.format(self.url)

        storage_data = self.app.get(storage_url).json['data']
        citations_data = self.app.get(citations_url).json['data']

        for addon in storage_data:
            assert_in('storage', addon['attributes']['categories'])

        for addon in citations_data:
            assert_in('citations', addon['attributes']['categories'])
