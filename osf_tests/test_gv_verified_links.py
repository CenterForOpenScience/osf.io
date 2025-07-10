import pytest
from unittest.mock import patch, MagicMock

from osf_tests.factories import ProjectFactory, UserFactory
from osf.external.gravy_valet import translations as gv_translations
from osf.external.gravy_valet import request_helpers as gv_requests


@pytest.mark.django_db
class TestGVVerifiedLinks:

    @pytest.fixture()
    def user(self):
        return UserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def mock_link_data(self):
        link1 = MagicMock()
        link1.attributes = {
            'title': 'Test Link 1',
            'url': 'https://example.com/1',
            'description': 'Test Description 1',
            'verified': True,
            'created': '2023-01-01T00:00:00Z',
            'modified': '2023-01-02T00:00:00Z',
        }

        link2 = MagicMock()
        link2.attributes = {
            'title': 'Test Link 2',
            'url': 'https://example.com/2',
            'description': 'Test Description 2',
            'verified': True,
            'created': '2023-01-03T00:00:00Z',
            'modified': '2023-01-04T00:00:00Z',
        }

        return [link1, link2]

    @patch('osf.external.gravy_valet.request_helpers.iterate_gv_results')
    def test_get_verified_links(self, mock_iterate_results, node, mock_link_data):
        mock_iterate_results.return_value = mock_link_data

        result = node.get_verified_links()

        assert len(result) == 2
        assert result[0]['title'] == 'Test Link 1'
        assert result[0]['url'] == 'https://example.com/1'
        assert result[1]['title'] == 'Test Link 2'
        assert result[1]['url'] == 'https://example.com/2'

        expected_endpoint = f"{gv_requests.ADDONS_ENDPOINT.format(addon_type=gv_requests.AddonType.LINK)}/{node._id}/verified-links"
        mock_iterate_results.assert_called_once_with(
            expected_endpoint,
            requesting_user=None,
            raise_on_error=True
        )

    @patch('osf.external.gravy_valet.request_helpers.iterate_gv_results')
    def test_get_verified_links_with_user(self, mock_iterate_results, node, user, mock_link_data):
        mock_iterate_results.return_value = mock_link_data

        result = gv_translations.get_verified_links(node._id, requesting_user=user)

        assert len(result) == 2

        expected_endpoint = f"{gv_requests.ADDONS_ENDPOINT.format(addon_type=gv_requests.AddonType.LINK)}/{node._id}/verified-links"
        mock_iterate_results.assert_called_once_with(
            expected_endpoint,
            requesting_user=user,
            raise_on_error=True
        )

    @patch('osf.external.gravy_valet.request_helpers.iterate_gv_results')
    def test_get_verified_links_empty(self, mock_iterate_results, node):
        mock_iterate_results.return_value = []

        result = node.get_verified_links()

        assert result == []

    @patch('osf.external.gravy_valet.request_helpers.iterate_gv_results')
    def test_get_verified_links_error_handling(self, mock_iterate_results, node):
        mock_iterate_results.side_effect = gv_requests.GVException('Test error')

        with pytest.raises(gv_requests.GVException):
            node.get_verified_links()
