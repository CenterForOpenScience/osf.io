from nose.tools import *
import mock

from tests.base import DbTestCase
from tests.factories import UserFactory, ProjectFactory
from website.addons.dataverse.model import AddonDataverseUserSettings, \
    AddonDataverseNodeSettings
from website.addons.dataverse.dvn.dataverse import Dataverse

from utils import create_mock_connection, DataverseAddonTestCase

class TestUtils(DataverseAddonTestCase):

    def test_mock_connection(self):
        # A connection with bad credentials fails
        failed_connection = create_mock_connection('wrong', 'info')
        assert_false(failed_connection)

        # A good connection has the correct parameters
        mock_connection = create_mock_connection()
        assert_equal(mock_connection.username, 'snowman')
        assert_equal(mock_connection.password, 'frosty')
        assert_equal(len(mock_connection.get_dataverses()), 3)
        assert_equal(mock_connection.get_dataverses()[0].__class__, Dataverse)
        assert_equal(
            mock_connection.get_dataverse(mock_connection.get_dataverses()[0].alias),
            mock_connection.get_dataverses()[0],
        )


