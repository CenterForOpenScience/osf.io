import pytest
from unittest import mock
from tests.base import ApiTestCase
from osf.utils import permissions
from osf_tests.factories import (
    AuthUserFactory,
    CollectionProviderFactory,
    ProjectFactory,
)


@pytest.fixture()
def provider():
    provider = CollectionProviderFactory()
    provider.update_group_permissions()
    return provider


@pytest.fixture()
def admin(provider):
    user = AuthUserFactory()
    provider.get_group(permissions.ADMIN).user_set.add(user)
    return user


@pytest.fixture()
def node(admin):
    return ProjectFactory(creator=admin)


class TestMaintenanceModeMiddlewareIntegration(ApiTestCase):
    MAINTENANCE_MOCK_PATH = 'api.base.middleware.MaintenanceMode.is_under_maintenance'

    def setUp(self):
        super().setUp()
        self.provider = CollectionProviderFactory()
        self.provider.update_group_permissions()
        self.admin = AuthUserFactory()
        self.provider.get_group(permissions.ADMIN).user_set.add(self.admin)
        self.node = ProjectFactory(creator=self.admin)

    @mock.patch(MAINTENANCE_MOCK_PATH, return_value=True)
    def test_middleware_blocks_post_when_maintenance_mode_on(self, mock_maintenance):
        url = f'/v2/nodes/{self.node._id}/'
        response = self.app.post_json(url, {}, expect_errors=True)
        assert response.status_code == 503
        assert response.json['meta']['maintenance_mode'] is True
        assert response.json['meta']['status_page'] == 'https://status.cos.io'

    @mock.patch(MAINTENANCE_MOCK_PATH, return_value=True)
    def test_middleware_blocks_patch_when_maintenance_mode_on(self, mock_maintenance):
        url = f'/v2/nodes/{self.node._id}/'
        response = self.app.patch_json(url, {}, expect_errors=True)
        assert response.status_code == 503
        assert response.json['meta']['maintenance_mode'] is True

    @mock.patch(MAINTENANCE_MOCK_PATH, return_value=True)
    def test_middleware_blocks_delete_when_maintenance_mode_on(self, mock_maintenance):
        url = f'/v2/nodes/{self.node._id}/'
        response = self.app.delete(url, expect_errors=True)

        assert response.status_code == 503
        assert response.json['meta']['maintenance_mode'] is True

    @mock.patch(MAINTENANCE_MOCK_PATH, return_value=False)
    def test_go_to_post_view_when_maintenance_mode_off(self, mock_maintenance):
        url = '/v2/nodes/'
        payload = {
            'data': {
                'type': 'nodes',
                'attributes': {'title': 'New Node', 'category': 'project'}
            }
        }
        response = self.app.post_json(url, payload, auth=self.admin.auth)
        assert response.status_code == 201

    @mock.patch(MAINTENANCE_MOCK_PATH, return_value=False)
    def test_go_to_post_view_if_maintenance_mode_off(self, mock_maintenance):
        url = f'/v2/nodes/{self.node._id}/'
        payload = {
            'data': {
                'id': self.node._id,
                'type': 'nodes',
                'attributes': {'title': 'Updated Title'}
            }
        }
        response = self.app.patch_json(url, payload, auth=self.admin.auth)
        assert response.status_code == 200

    @mock.patch(MAINTENANCE_MOCK_PATH, return_value=False)
    def test_go_to_delete_view_if_maintenance_mode_off(self, mock_maintenance):
        url = f'/v2/nodes/{self.node._id}/'
        response = self.app.delete(url, auth=self.admin.auth)
        assert response.status_code == 204
