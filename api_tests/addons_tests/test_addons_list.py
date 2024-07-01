import pytest

from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
class TestAddonsList:

    def test_filter_by_category(self, app):
        url = f'/{API_BASE}addons/'
        url_storage = f'{url}?filter[categories]=storage'
        url_citations = f'{url}?filter[categories]=citations'

        data_storage = app.get(url_storage).json['data']
        data_citations = app.get(url_citations).json['data']

        for addon in data_storage:
            assert 'storage' in addon['attributes']['categories']

        for addon in data_citations:
            assert 'citations' in addon['attributes']['categories']
