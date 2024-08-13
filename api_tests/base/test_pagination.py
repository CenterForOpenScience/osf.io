from osf_tests import factories
from tests.base import ApiTestCase

from api.base import settings
from api.base.pagination import MaxSizePagination


class TestMaxPagination(ApiTestCase):
    def test_no_query_param_alters_page_size(self):
        assert MaxSizePagination.page_size_query_param is None, 'Adding variable page sizes to the paginator ' +\
            'requires tests to ensure that you can\'t request more than the class\'s maximum number of values.'


class TestJSONAPIPagination(ApiTestCase):

    def setUp(self):
        super().setUp()

        self.url_version_2_0 = f'/{settings.API_BASE}nodes/'
        self.url_version_2_1 = '/{}nodes/?version=2.1'.format(
            settings.API_BASE)
        self.user = factories.AuthUserFactory()

        for i in range(0, 11):
            factories.ProjectFactory(creator=self.user)

    def test_pagination_links_v2(self):
        res = self.app.get(self.url_version_2_0, auth=self.user)
        assert res.status_code == 200
        links = res.json['links']
        meta = res.json['links']['meta']
        assert 'self' not in links
        assert 'first' in links
        assert 'next' in links
        assert 'last' in links
        assert 'prev' in links
        assert 'meta' in links
        assert 'total' in meta
        assert 'per_page' in meta

    def test_pagination_links_updated_version(self):
        res = self.app.get(self.url_version_2_1, auth=self.user)
        assert res.status_code == 200
        links = res.json['links']
        meta = res.json['meta']
        assert 'self' in links
        assert 'first' in links
        assert 'next' in links
        assert 'last' in links
        assert 'prev' in links
        assert 'meta' not in links
        assert 'total' in meta
        assert 'per_page' in meta
