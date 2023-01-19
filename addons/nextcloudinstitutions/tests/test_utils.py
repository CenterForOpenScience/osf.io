import unittest
from unittest import mock

import pytest

from addons.nextcloud.tests.factories import NodeSettingsFactory
from addons.nextcloudinstitutions.utils import get_timestamp, set_timestamp


@pytest.mark.django_db
class TestUtils(unittest.TestCase):

    def setUp(self):
        super(TestUtils, self).setUp()
        self.node = NodeSettingsFactory()

    def test_get_timestamp_return_none(self):
        mock_metadata = mock.MagicMock()
        mock_metadata.return_value = None
        mock_client = mock.MagicMock()
        mock_client.login.return_value = True

        path = 'test_path'
        provider_name = 'nextcloud'
        with mock.patch('addons.nextcloudinstitutions.utils.NextcloudClient.login', mock_client):
            with mock.patch('addons.nextcloudinstitutions.utils.MetadataClient.get_metadata', mock_metadata):
                res = get_timestamp(self.node, path, provider_name)
                assert res == (None, None, None)

    def test_get_timestamp(self):
        mock_metadata = mock.MagicMock()
        mock_metadata.return_value = ['res_value']
        mock_client = mock.MagicMock()
        mock_client.login.return_value = True
        mock_get_attribute = mock.MagicMock()
        mock_get_attribute.return_value = 'eW91ciB0ZXh0'

        path = 'test_path'
        provider_name = 'nextcloud'
        with mock.patch('addons.nextcloudinstitutions.utils.MetadataClient.get_attribute', mock_get_attribute):
            with mock.patch('addons.nextcloudinstitutions.utils.NextcloudClient.login', mock_client):
                with mock.patch('addons.nextcloudinstitutions.utils.MetadataClient.get_metadata', mock_metadata):
                    res = get_timestamp(self.node, path, provider_name)
                    assert res != (None, None, None)

    def test_get_timestamp_get_attribute_return_none(self):
        mock_metadata = mock.MagicMock()
        mock_metadata.return_value = ['res_value']
        mock_client = mock.MagicMock()
        mock_client.login.return_value = True
        mock_get_attribute = mock.MagicMock()
        mock_get_attribute.return_value = None

        path = 'test_path'
        provider_name = 'nextcloud'
        with mock.patch('addons.nextcloudinstitutions.utils.MetadataClient.get_attribute', mock_get_attribute):
            with mock.patch('addons.nextcloudinstitutions.utils.NextcloudClient.login', mock_client):
                with mock.patch('addons.nextcloudinstitutions.utils.MetadataClient.get_metadata', mock_metadata):
                    res = get_timestamp(self.node, path, provider_name)
                    assert res != (None, None, None)

    def test_set_timestamp_with_context_not_none(self):
        mock_metadata = mock.MagicMock()
        mock_metadata.return_value = None
        mock_client = mock.MagicMock()
        mock_client.login.return_value = True

        path = 'test_path'
        timestamp_data = b'abcxyz'
        provider_name = 'nextcloud'
        timestamp_status = 1
        context = {
            'url': 'http://test.xyz',
            'username': 'username_data',
            'password': 'password_test'
        }
        with mock.patch('addons.nextcloudinstitutions.utils.NextcloudClient.login', mock_client):
            with mock.patch('addons.nextcloudinstitutions.utils.MetadataClient.set_metadata', mock_metadata):
                set_timestamp(self.node, path, timestamp_data, timestamp_status, context, provider_name)

    def test_set_timestamp_with_context_is_none(self):
        mock_metadata = mock.MagicMock()
        mock_metadata.return_value = 'abc'
        mock_client = mock.MagicMock()
        mock_client.login.return_value = True

        path = 'test_path'
        timestamp_data = b'abcxyz'
        provider_name = 'nextcloud'
        timestamp_status = 1
        with mock.patch('addons.nextcloudinstitutions.utils.NextcloudClient.login', mock_client):
            with mock.patch('addons.nextcloudinstitutions.utils.MetadataClient.set_metadata', mock_metadata):
                set_timestamp(self.node, path, timestamp_data, timestamp_status, None, provider_name)
