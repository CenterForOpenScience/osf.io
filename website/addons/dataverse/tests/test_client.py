from nose.tools import *
import mock
import unittest

from dataverse import Connection, Dataverse, DataverseFile, Dataset
from dataverse.exceptions import UnauthorizedError

from framework.exceptions import HTTPError
from website.addons.dataverse.tests.utils import DataverseAddonTestCase
from website.addons.dataverse.client import (_connect, delete_file, upload_file,
    get_file, get_file_by_id, get_files, publish_dataset, get_datasets, get_dataset,
    get_dataverses, get_dataverse, connect_from_settings, connect_or_401,
    connect_from_settings_or_401)
from website.addons.dataverse.model import AddonDataverseUserSettings
from website.addons.dataverse import settings


class TestClient(DataverseAddonTestCase):

    def setUp(self):

        super(TestClient, self).setUp()

        self.mock_connection = mock.create_autospec(Connection)
        self.mock_dataverse = mock.create_autospec(Dataverse)
        self.mock_dataset = mock.create_autospec(Dataset)
        self.mock_file = mock.create_autospec(DataverseFile)

        self.mock_file.dataset = self.mock_dataset
        self.mock_dataset.dataverse = self.mock_dataverse
        self.mock_dataverse.connection = self.mock_connection

    @mock.patch('website.addons.dataverse.client.Connection')
    def test_connect(self, mock_dvn_connection):
        mock_obj = mock.create_autospec(Connection)
        mock_dvn_connection.return_value = mock_obj

        c = _connect('My user', 'My pw', 'My host')

        mock_dvn_connection.assert_called_once_with(
            username='My user', password='My pw', host='My host',
        )

        assert_true(c)

    @mock.patch('website.addons.dataverse.client.Connection')
    def test_connect_fail(self, mock_dvn_connection):
        mock_dvn_connection.side_effect = UnauthorizedError()

        with assert_raises(UnauthorizedError) as e:
            c = _connect('My user', 'My pw', 'My host')

        mock_dvn_connection.assert_called_once_with(
            username='My user', password='My pw', host='My host',
        )

    @mock.patch('website.addons.dataverse.client.Connection')
    def test_connect_or_401(self, mock_dvn_connection):
        mock_obj = mock.create_autospec(Connection)
        mock_obj.connected = True
        mock_dvn_connection.return_value = mock_obj

        c = connect_or_401('My user', 'My pw', 'My host')

        mock_dvn_connection.assert_called_once_with(
            username='My user', password='My pw', host='My host',
        )

        assert_true(c)

    @mock.patch('website.addons.dataverse.client.Connection')
    def test_connect_or_401_forbidden(self, mock_dvn_connection):
        mock_dvn_connection.side_effect = UnauthorizedError()

        with assert_raises(HTTPError) as cm:
            connect_or_401('My user', 'My pw', 'My host')

        mock_dvn_connection.assert_called_once_with(
            username='My user', password='My pw', host='My host',
        )

        assert_equal(cm.exception.code, 401)

    @mock.patch('website.addons.dataverse.client._connect')
    def test_connect_from_settings(self, mock_connect):
        user_settings = AddonDataverseUserSettings()
        user_settings.dataverse_username = 'Something ridiculous'
        user_settings.dataverse_password = 'm04rR1d1cul0u$'

        connection = connect_from_settings(user_settings)
        assert_true(connection)
        mock_connect.assert_called_once_with(
            user_settings.dataverse_username,
            user_settings.dataverse_password,
        )

    def test_connect_from_settings_none(self):
        connection = connect_from_settings(None)
        assert_is_none(connection)


    @mock.patch('website.addons.dataverse.client.connect_or_401')
    def test_connect_from_settings_or_401(self, mock_connect):
        user_settings = AddonDataverseUserSettings()
        user_settings.dataverse_username = 'Something ridiculous'
        user_settings.dataverse_password = 'm04rR1d1cul0u$'

        connection = connect_from_settings_or_401(user_settings)
        assert_true(connection)
        mock_connect.assert_called_once_with(
            user_settings.dataverse_username,
            user_settings.dataverse_password,
        )

    def test_connect_from_settings_or_401_none(self):
        connection = connect_from_settings_or_401(None)
        assert_is_none(connection)

    @mock.patch('website.addons.dataverse.client.Connection')
    def test_connect_from_settings_or_401_forbidden(self, mock_dvn_connection):
        mock_dvn_connection.side_effect = UnauthorizedError()

        user_settings = AddonDataverseUserSettings()
        user_settings.dataverse_username = 'Something ridiculous'
        user_settings.dataverse_password = 'm04rR1d1cul0u$'

        with assert_raises(HTTPError) as e:
            connect_from_settings_or_401(user_settings)

        mock_dvn_connection.assert_called_once_with(
            username=user_settings.dataverse_username,
            password=user_settings.dataverse_password,
            host=settings.HOST,
        )

        assert_equal(e.exception.code, 401)

    def test_delete_file(self):
        delete_file(self.mock_file)
        self.mock_dataset.delete_file.assert_called_once_with(self.mock_file)

    def test_upload_file(self):
        upload_file(self.mock_dataset, 'filename.txt', b'File Content')
        self.mock_dataset.upload_file.assert_called_once_with('filename.txt',
                                                             b'File Content')

    def test_get_file(self):
        published = True
        get_file(self.mock_dataset, 'filename.txt', published)
        self.mock_dataset.get_file.assert_called_once_with('filename.txt', published)

    def test_get_file_by_id(self):
        published = True
        get_file_by_id(self.mock_dataset, '12345', published)
        self.mock_dataset.get_file_by_id.assert_called_once_with('12345', published)

    def test_get_files(self):
        published = True
        get_files(self.mock_dataset, published)
        self.mock_dataset.get_files.assert_called_once_with(published)

    def test_publish_dataset(self):
        publish_dataset(self.mock_dataset)
        self.mock_dataset.publish.assert_called_once_with()

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

        datasets, bad_datasets = get_datasets(self.mock_dataverse)
        self.mock_dataverse.get_datasets.assert_called_once_with()
        assert_in(mock_dataset1, datasets)
        assert_in(mock_dataset2, datasets)
        assert_in(mock_dataset3, datasets)
        assert_equal(bad_datasets, [])

    def test_get_datasets_no_dataverse(self):
        datasets, bad_datasets = get_datasets(None)
        assert_equal(datasets, [])
        assert_equal(bad_datasets, [])

    @unittest.skip('Functionality was removed due to high number of requests.')
    def test_get_datasets_some_bad(self):
        mock_dataset1 = mock.create_autospec(Dataset)
        mock_dataset2 = mock.create_autospec(Dataset)
        mock_dataset3 = mock.create_autospec(Dataset)
        error = UnicodeDecodeError('utf-8', b'', 1, 2, 'jeepers')
        mock_dataset1.get_state.return_value = 'DRAFT'
        mock_dataset2.get_state.side_effect = error
        mock_dataset3.get_state.return_value = 'DEACCESSIONED'
        self.mock_dataverse.get_datasets.return_value = [
            mock_dataset1, mock_dataset2, mock_dataset3
        ]

        datasets, bad_datasets = get_datasets(self.mock_dataverse)
        self.mock_dataverse.get_datasets.assert_called_once_with()
        assert_equal([mock_dataset1], datasets)
        assert_equal([mock_dataset2], bad_datasets)

    def test_get_dataset(self):
        self.mock_dataset.get_state.return_value = 'DRAFT'
        self.mock_dataverse.get_dataset_by_doi.return_value = self.mock_dataset

        s = get_dataset(self.mock_dataverse, 'My hdl')
        self.mock_dataverse.get_dataset_by_doi.assert_called_once_with('My hdl')

        assert_equal(s, self.mock_dataset)

    def test_get_deaccessioned_dataset(self):
        self.mock_dataset.get_state.return_value = 'DEACCESSIONED'
        self.mock_dataverse.get_dataset_by_doi.return_value = self.mock_dataset

        with assert_raises(HTTPError) as e:
            s = get_dataset(self.mock_dataverse, 'My hdl')

        self.mock_dataverse.get_dataset_by_doi.assert_called_once_with('My hdl')
        assert_equal(e.exception.code, 410)

    def test_get_bad_dataset(self):
        error = UnicodeDecodeError('utf-8', b'', 1, 2, 'jeepers')
        self.mock_dataset.get_state.side_effect = error
        self.mock_dataverse.get_dataset_by_doi.return_value = self.mock_dataset

        with assert_raises(HTTPError) as e:
            s = get_dataset(self.mock_dataverse, 'My hdl')
        self.mock_dataverse.get_dataset_by_doi.assert_called_once_with('My hdl')
        assert_equal(e.exception.code, 406)

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

        assert_in(published_dv, dvs)
        assert_not_in(unpublished_dv, dvs)

    def test_get_dataverse(self):
        type(self.mock_dataverse).is_published = mock.PropertyMock(return_value=True)
        self.mock_connection.get_dataverse.return_value = self.mock_dataverse

        d = get_dataverse(self.mock_connection, 'ALIAS')
        self.mock_connection.get_dataverse.assert_called_once_with('ALIAS')

        assert_equal(d, self.mock_dataverse)

    def test_get_unpublished_dataverse(self):
        type(self.mock_dataverse).is_published = mock.PropertyMock(return_value=False)
        self.mock_connection.get_dataverse.return_value = self.mock_dataverse

        d = get_dataverse(self.mock_connection, 'ALIAS')
        self.mock_connection.get_dataverse.assert_called_once_with('ALIAS')

        assert_equal(d, None)
