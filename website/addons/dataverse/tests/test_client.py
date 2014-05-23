from nose.tools import *
import mock

from website.addons.dataverse.tests.utils import DataverseAddonTestCase
from website.addons.dataverse.client import connect, delete_file, upload_file, \
    get_file, get_file_by_id, get_files, release_study
from website.addons.dataverse.dvn.connection import DvnConnection
from website.addons.dataverse.dvn.file import DvnFile
from website.addons.dataverse.dvn.study import Study
from website.addons.dataverse.settings import TEST_CERT


class TestClient(DataverseAddonTestCase):

    def setUp(self):
        self.mock_study = mock.create_autospec(Study)
        self.mock_file = mock.create_autospec(DvnFile)
        self.mock_file.hostStudy = self.mock_study

    @mock.patch('website.addons.dataverse.client.DvnConnection')
    def test_connect(self, mock_dvn_connection):
        mock_obj = mock.create_autospec(DvnConnection)
        mock_obj.connected = True
        mock_dvn_connection.return_value = mock_obj

        c = connect('My user', 'My pw', 'My host')

        mock_dvn_connection.assert_called_once_with(
            username='My user', password='My pw', host='My host', cert=TEST_CERT
        )

        assert_true(c)

    @mock.patch('website.addons.dataverse.client.DvnConnection')
    def test_connect_fail(self, mock_dvn_connection):
        mock_obj = mock.create_autospec(DvnConnection)
        mock_obj.connected = False
        mock_dvn_connection.return_value = mock_obj

        c = connect('My user', 'My pw', 'My host')

        mock_dvn_connection.assert_called_once_with(
            username='My user', password='My pw', host='My host', cert=TEST_CERT
        )

        assert_equal(c, None)

    def test_delete_file(self):
        delete_file(self.mock_file)
        self.mock_study.delete_file.assert_called_once_with(self.mock_file)

    def test_upload_file(self):
        upload_file(self.mock_study, 'filename.txt', b'File Content')
        self.mock_study.add_file_obj.assert_called_once_with('filename.txt',
                                                             b'File Content')

    def test_get_file(self):
        released = True
        get_file(self.mock_study, 'filename.txt', released)
        self.mock_study.get_file.assert_called_once_with('filename.txt', released)

    def test_get_file_by_id(self):
        released = True
        get_file_by_id(self.mock_study, '12345', released)
        self.mock_study.get_file_by_id.assert_called_once_with('12345', released)

    def test_get_files(self):
        released = True
        get_files(self.mock_study, released)
        self.mock_study.get_files.assert_called_once_with(released)

    def test_release_study(self):
        release_study(self.mock_study)
        self.mock_study.release.assert_called_once_with()
