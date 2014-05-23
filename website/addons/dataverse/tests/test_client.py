from nose.tools import *
import mock

from website.addons.dataverse.tests.utils import DataverseAddonTestCase
from website.addons.dataverse.client import connect
from website.addons.dataverse.dvn.connection import DvnConnection
from website.addons.dataverse.settings import TEST_CERT


class TestClient(DataverseAddonTestCase):

    @mock.patch('website.addons.dataverse.client.DvnConnection')
    def test_connect(self, mock_dvn_connection):
        mock_obj = mock.create_autospec(DvnConnection)
        mock_obj.connected = True
        mock_dvn_connection.return_value = mock_obj

        c = connect('My user', 'My pw', 'My host')

        mock_dvn_connection.assert_called_with(
            username='My user', password='My pw', host='My host', cert=TEST_CERT
        )

        assert_true(c)

    @mock.patch('website.addons.dataverse.client.DvnConnection')
    def test_connect_fail(self, mock_dvn_connection):
        mock_obj = mock.create_autospec(DvnConnection)
        mock_obj.connected = False
        mock_dvn_connection.return_value = mock_obj

        c = connect('My user', 'My pw', 'My host')

        mock_dvn_connection.assert_called_with(
            username='My user', password='My pw', host='My host', cert=TEST_CERT
        )

        assert_equal(c, None)