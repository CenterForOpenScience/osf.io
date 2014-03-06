import mock
from website.addons.dataverse.dvn.connection import DvnConnection


def create_mock_connection(user='User 1'):
    """Factory for creating mock dataverse.
    """

    connection_mock = mock.create_autospec(DvnConnection)
    dataverse_mock = connection_mock.get_dataverses()
