import pytest
from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
class TestAddonDetail:
    """
    Tests Add Detail endpoint
    """

    def test_addon_detail(self, app):
        resp = app.get(f'/{API_BASE}addons/s3/')

        assert resp.status_code == 200
        data = resp.json['data']
        assert data['attributes']['name'] == 'Amazon S3'
        assert data['attributes']['category'] == 'storage'
