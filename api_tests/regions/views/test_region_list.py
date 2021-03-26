import pytest

from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
class TestRegionList:
    @pytest.fixture()
    def regions_url(self):
        return f'/{API_BASE}regions/'

    def test_region_list(self, app, regions_url):
        res = app.get(regions_url)

        data = res.json['data']
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(data) == 1

        assert data[0]['attributes']['name'] == 'United States'
        assert data[0]['id'] == 'us'
