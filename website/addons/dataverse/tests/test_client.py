from nose.tools import *
import mock

from website.addons.dataverse.tests.utils import DataverseAddonTestCase
from website.addons.dataverse.client import (connect, delete_file, upload_file,
    get_file, get_file_by_id, get_files, release_study, get_studies, get_study,
    get_dataverses, get_dataverse)
from website.addons.dataverse.dvn.connection import DvnConnection
from website.addons.dataverse.dvn.dataverse import Dataverse
from website.addons.dataverse.dvn.file import DvnFile
from website.addons.dataverse.dvn.study import Study
from website.addons.dataverse.settings import TEST_CERT


class TestClient(DataverseAddonTestCase):

    def setUp(self):
        self.mock_connection = mock.create_autospec(DvnConnection)
        self.mock_dataverse = mock.create_autospec(Dataverse)
        self.mock_study = mock.create_autospec(Study)
        self.mock_file = mock.create_autospec(DvnFile)

        self.mock_file.hostStudy = self.mock_study
        self.mock_study.hostDataverse = self.mock_dataverse
        self.mock_dataverse.connection = self.mock_connection

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

    def test_get_studies(self):
        mock_study1 = mock.create_autospec(Study)
        mock_study2 = mock.create_autospec(Study)
        mock_study3 = mock.create_autospec(Study)
        mock_study1.get_state.return_value = 'DRAFT'
        mock_study2.get_state.return_value = 'RELEASED'
        mock_study3.get_state.return_value = 'DEACCESSIONED'
        self.mock_dataverse.get_studies.return_value = [
            mock_study1, mock_study2, mock_study3
        ]

        studies = get_studies(self.mock_dataverse)
        self.mock_dataverse.get_studies.assert_called_once_with()
        assert_in(mock_study1, studies)
        assert_in(mock_study2, studies)
        assert_not_in(mock_study3, studies)

    def test_get_studies_no_dataverse(self):
        studies = get_studies(None)
        assert_equal(studies, None)

    def test_get_study(self):
        self.mock_study.get_state.return_value = 'DRAFT'
        self.mock_dataverse.get_study_by_hdl.return_value = self.mock_study

        s = get_study(self.mock_dataverse, 'My hdl')
        self.mock_dataverse.get_study_by_hdl.assert_called_once_with('My hdl')

        assert_equal(s, self.mock_study)

    def test_get_deaccessioned_study(self):
        self.mock_study.get_state.return_value = 'DEACCESSIONED'
        self.mock_dataverse.get_study_by_hdl.return_value = self.mock_study

        s = get_study(self.mock_dataverse, 'My hdl')
        self.mock_dataverse.get_study_by_hdl.assert_called_once_with('My hdl')

        assert_equal(s, None)

    def test_get_dataverses(self):
        released_dv = mock.create_autospec(Dataverse)
        unreleased_dv = mock.create_autospec(Dataverse)
        type(released_dv).is_released = mock.PropertyMock(return_value=True)
        type(unreleased_dv).is_released = mock.PropertyMock(return_value=False)
        self.mock_connection.get_dataverses.return_value = [
            released_dv, unreleased_dv
        ]

        dvs = get_dataverses(self.mock_connection)
        self.mock_connection.get_dataverses.assert_called_once_with()

        assert_in(released_dv, dvs)
        assert_not_in(unreleased_dv, dvs)

    def test_get_dataverse(self):
        type(self.mock_dataverse).is_released = mock.PropertyMock(return_value=True)
        self.mock_connection.get_dataverse.return_value = self.mock_dataverse

        d = get_dataverse(self.mock_connection, 'ALIAS')
        self.mock_connection.get_dataverse.assert_called_once_with('ALIAS')

        assert_equal(d, self.mock_dataverse)

    def test_get_unreleased_dataverse(self):
        type(self.mock_dataverse).is_released = mock.PropertyMock(return_value=False)
        self.mock_connection.get_dataverse.return_value = self.mock_dataverse

        d = get_dataverse(self.mock_connection, 'ALIAS')
        self.mock_connection.get_dataverse.assert_called_once_with('ALIAS')

        assert_equal(d, None)