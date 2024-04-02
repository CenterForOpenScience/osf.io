from unittest import mock
import pytest
import unittest

from dataverse import Connection, Dataverse, DataverseFile, Dataset
from dataverse.exceptions import UnauthorizedError

from addons.dataverse.models import NodeSettings
from addons.dataverse.tests.utils import DataverseAddonTestCase, create_external_account
from framework.exceptions import HTTPError
from addons.dataverse.client import (
    _connect, get_files, publish_dataset, get_datasets, get_dataset,
    get_dataverses, get_dataverse, connect_from_settings, connect_or_error,
    connect_from_settings_or_401,
)
from addons.dataverse import settings

pytestmark = pytest.mark.django_db


class TestClient(DataverseAddonTestCase, unittest.TestCase):

    def setUp(self):
        super().setUp()

        self.host = 'some.host.url'
        self.token = 'some-fancy-api-token-which-is-long'

        self.mock_connection = mock.create_autospec(Connection)
        self.mock_dataverse = mock.create_autospec(Dataverse)
        self.mock_dataset = mock.create_autospec(Dataset)
        self.mock_file = mock.create_autospec(DataverseFile)

        self.mock_file.dataset = self.mock_dataset
        self.mock_dataset.dataverse = self.mock_dataverse
        self.mock_dataverse.connection = self.mock_connection

    @mock.patch('addons.dataverse.client.Connection')
    def test_connect(self, mock_connection):
        mock_connection.return_value = mock.create_autospec(Connection)
        c = _connect(self.host, self.token)

        mock_connection.assert_called_once_with(self.host, self.token)
        assert c

    @mock.patch('addons.dataverse.client.Connection')
    def test_connect_fail(self, mock_connection):
        mock_connection.side_effect = UnauthorizedError()
        with pytest.raises(UnauthorizedError):
            _connect(self.host, self.token)

        mock_connection.assert_called_once_with(self.host, self.token)

    @mock.patch('addons.dataverse.client.Connection')
    def test_connect_or_error(self, mock_connection):
        mock_connection.return_value = mock.create_autospec(Connection)
        c = connect_or_error(self.host, self.token)

        mock_connection.assert_called_once_with(self.host, self.token)
        assert c

    @mock.patch('addons.dataverse.client.Connection')
    def test_connect_or_error_returns_401_when_client_raises_unauthorized_error(self, mock_connection):
        mock_connection.side_effect = UnauthorizedError()
        with pytest.raises(HTTPError) as cm:
            connect_or_error(self.host, self.token)

        mock_connection.assert_called_once_with(self.host, self.token)
        assert cm.value.code == 401

    @mock.patch('addons.dataverse.client._connect')
    def test_connect_from_settings(self, mock_connect):
        node_settings = NodeSettings()
        node_settings.external_account = create_external_account(
            self.host, self.token,
        )

        connection = connect_from_settings(node_settings)
        assert connection
        mock_connect.assert_called_once_with(self.host, self.token)

    def test_connect_from_settings_none(self):
        connection = connect_from_settings(None)
        assert connection is None

    @mock.patch('addons.dataverse.client._connect')
    def test_connect_from_settings_or_401(self, mock_connect):
        node_settings = NodeSettings()
        node_settings.external_account = create_external_account(
            self.host, self.token,
        )

        connection = connect_from_settings_or_401(node_settings)
        assert connection
        mock_connect.assert_called_once_with(self.host, self.token)

    def test_connect_from_settings_or_401_none(self):
        connection = connect_from_settings_or_401(None)
        assert connection is None

    @mock.patch('addons.dataverse.client.Connection')
    def test_connect_from_settings_or_401_forbidden(self, mock_connection):
        mock_connection.side_effect = UnauthorizedError()
        node_settings = NodeSettings()
        node_settings.external_account = create_external_account(
            self.host, self.token,
        )

        with pytest.raises(HTTPError) as e:
            connect_from_settings_or_401(node_settings)

        mock_connection.assert_called_once_with(self.host, self.token)
        assert e.value.code == 401

    def test_get_files(self):
        published = False
        get_files(self.mock_dataset, published)
        self.mock_dataset.get_files.assert_called_once_with('latest')

    def test_get_files_published(self):
        published = True
        get_files(self.mock_dataset, published)
        self.mock_dataset.get_files.assert_called_once_with('latest-published')

    def test_publish_dataset(self):
        publish_dataset(self.mock_dataset)
        self.mock_dataset.publish.assert_called_once_with()

    def test_publish_dataset_unpublished_dataverse(self):
        type(self.mock_dataverse).is_published = mock.PropertyMock(return_value=False)
        with pytest.raises(HTTPError) as e:
            publish_dataset(self.mock_dataset)

        assert not self.mock_dataset.publish.called
        assert e.value.code == 405

    def test_get_datasets(self):
        mock_dataset1 = mock.create_autospec(Dataset)
        mock_dataset2 = mock.create_autospec(Dataset)
        mock_dataset3 = mock.create_autospec(Dataset)
        mock_dataset1.get_state.return_value = 'DRAFT'
        mock_dataset2.get_state.return_value = 'RELEASED'
        mock_dataset3.get_state.return_value = 'DEACCESSIONED'
        self.mock_dataverse.get_datasets.return_value = [
            mock_dataset1, mock_dataset2, mock_dataset3
        ]

        datasets = get_datasets(self.mock_dataverse)
        assert self.mock_dataverse.get_datasets.assert_called_once_with(timeout=settings.REQUEST_TIMEOUT) is None
        assert mock_dataset1 in datasets
        assert mock_dataset2 in datasets
        assert mock_dataset3 in datasets

    def test_get_datasets_no_dataverse(self):
        datasets = get_datasets(None)
        assert datasets == []

    def test_get_dataset(self):
        self.mock_dataset.get_state.return_value = 'DRAFT'
        self.mock_dataverse.get_dataset_by_doi.return_value = self.mock_dataset

        s = get_dataset(self.mock_dataverse, 'My hdl')
        assert self.mock_dataverse.get_dataset_by_doi.assert_called_once_with('My hdl', timeout=settings.REQUEST_TIMEOUT) is None

        assert s == self.mock_dataset

    @mock.patch('dataverse.dataverse.requests')
    def test_get_dataset_calls_patched_timeout_method(self, mock_requests):
        # Verify optional timeout parameter is passed to requests by dataverse client.
        # https://github.com/IQSS/dataverse-client-python/pull/27
        dataverse = Dataverse(mock.Mock(), mock.Mock())
        dataverse.connection.auth = 'me'
        dataverse.collection.get.return_value = '123'
        mock_requests.get.side_effect = Exception('Done Testing')

        with pytest.raises(Exception) as e:
            get_dataset(dataverse, 'My hdl')
        assert mock_requests.get.assert_called_once_with('123', auth='me', timeout=settings.REQUEST_TIMEOUT) is None
        assert str(e.value) == 'Done Testing'

    def test_get_deaccessioned_dataset(self):
        self.mock_dataset.get_state.return_value = 'DEACCESSIONED'
        self.mock_dataverse.get_dataset_by_doi.return_value = self.mock_dataset

        with pytest.raises(HTTPError) as e:
            get_dataset(self.mock_dataverse, 'My hdl')

        assert self.mock_dataverse.get_dataset_by_doi.assert_called_once_with('My hdl', timeout=settings.REQUEST_TIMEOUT) is None
        assert e.value.code == 410

    def test_get_bad_dataset(self):
        error = UnicodeDecodeError('utf-8', b'', 1, 2, 'jeepers')
        self.mock_dataset.get_state.side_effect = error
        self.mock_dataverse.get_dataset_by_doi.return_value = self.mock_dataset

        with pytest.raises(HTTPError) as e:
            get_dataset(self.mock_dataverse, 'My hdl')
        assert self.mock_dataverse.get_dataset_by_doi.assert_called_once_with('My hdl', timeout=settings.REQUEST_TIMEOUT) is None
        assert e.value.code == 406

    def test_get_dataverses(self):
        published_dv = mock.create_autospec(Dataverse)
        unpublished_dv = mock.create_autospec(Dataverse)
        type(published_dv).is_published = mock.PropertyMock(return_value=True)
        type(unpublished_dv).is_published = mock.PropertyMock(return_value=False)
        self.mock_connection.get_dataverses.return_value = [
            published_dv, unpublished_dv
        ]

        dvs = get_dataverses(self.mock_connection)
        self.mock_connection.get_dataverses.assert_called_once_with()

        assert published_dv in dvs
        assert unpublished_dv in dvs
        assert len(dvs) == 2

    def test_get_dataverse(self):
        type(self.mock_dataverse).is_published = mock.PropertyMock(return_value=True)
        self.mock_connection.get_dataverse.return_value = self.mock_dataverse

        d = get_dataverse(self.mock_connection, 'ALIAS')
        self.mock_connection.get_dataverse.assert_called_once_with('ALIAS')

        assert d == self.mock_dataverse

    def test_get_unpublished_dataverse(self):
        type(self.mock_dataverse).is_published = mock.PropertyMock(return_value=False)
        self.mock_connection.get_dataverse.return_value = self.mock_dataverse

        d = get_dataverse(self.mock_connection, 'ALIAS')
        self.mock_connection.get_dataverse.assert_called_once_with('ALIAS')

        assert d == self.mock_dataverse
