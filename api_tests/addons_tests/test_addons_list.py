import pytest

from api.base.settings.defaults import API_BASE

@pytest.mark.django_db
class TestAddonsList:

    def test_filter_by_category(self, app):
        url = '/{}addons/'.format(API_BASE)
        url_storage = '{}?filter[categories]=storage'.format(url)
        url_citations = '{}?filter[categories]=citations'.format(url)

        data_storage = app.get(url_storage).json['data']
        data_citations = app.get(url_citations).json['data']

        for addon in data_storage:
            assert 'storage' in addon['attributes']['categories']

        for addon in data_citations:
            assert 'citations' in addon['attributes']['categories']
