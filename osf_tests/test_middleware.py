import json
import pytest
from unittest import mock

class TestMaintenanceModeMiddlewareIntegration:

    MAINTENANCE_MOCK_PATH = 'api.base.middleware.MaintenanceMode.is_under_maintenance'

    @mock.patch(MAINTENANCE_MOCK_PATH, return_value=True)
    def test_bypasses_v2_root_if_maintenance_mode_on(self, mock_maintenance, client):
        response = client.get('/v2')
        assert response.status_code != 503
        mock_maintenance.assert_not_called()

    @pytest.mark.parametrize('method', ['post', 'patch', 'put', 'delete'])
    @mock.patch(MAINTENANCE_MOCK_PATH, return_value=True)
    def test_middleware_blocks_different_requests_if_maintenance_mode_on(self, mock_maintenance, client, method):
        client_method = getattr(client, method)
        response = client_method('/v2/nodes/', data={}, content_type='application/json')
        assert response.status_code == 503
        data = json.loads(response.content)
        assert data['meta']['maintenance_mode'] is True
        assert data['meta']['status_page'] == 'https://status.cos.io'

    @mock.patch(MAINTENANCE_MOCK_PATH, return_value=False)
    def test_passes_through_when_maintenance_mode_off(self, mock_maintenance, client):
        response = client.get('/v2/nodes/')
        assert response.status_code != 503
