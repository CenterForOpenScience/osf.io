# -*- coding: utf-8 -*-
import pytest
from osf_tests.factories import AuthUserFactory, ProjectFactory

from api.base import settings
from api.base.pagination import MaxSizePagination

class TestMaxPagination:
    def test_no_query_param_alters_page_size(self):
        assert MaxSizePagination.page_size_query_param is None, 'Adding variable page sizes to the paginator ' +\
            'requires tests to ensure that you can\'t request more than the class\'s maximum number of values.'

@pytest.mark.django_db
class TestJSONAPIPagination:

    def test_json_api_pagination_by_version(self, app):
        url_version_2_0 = '/{}nodes/'.format(settings.API_BASE)
        url_version_2_1 = '/{}nodes/?version=2.1'.format(settings.API_BASE)
        user = AuthUserFactory()
        for i in range(0,11):
            ProjectFactory(creator=user)

        #test_pagination_links_v2
        res = app.get(url_version_2_0, auth=user)
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

        #test_pagination_links_updated_version
        res = app.get(url_version_2_1, auth=user)
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
