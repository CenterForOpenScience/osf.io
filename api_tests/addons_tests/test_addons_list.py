import pytest
from api.base.settings.defaults import API_BASE

@pytest.mark.django_db
class TestAddonsList:

    def test_filter_by_category(self, app):
        url = '/{}addons/'.format(API_BASE)
        storage_url = '{}?filter[categories]=storage'.format(url)
        citations_url = '{}?filter[categories]=citations'.format(url)

        storage_data = app.get(storage_url).json['data']
        citations_data = app.get(citations_url).json['data']

        for addon in storage_data:
            assert 'storage' in addon['attributes']['categories']

        for addon in citations_data:
            assert 'citations' in addon['attributes']['categories']
