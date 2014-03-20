import mock
from website.addons.dataverse.dvn.connection import DvnConnection


def create_mock_connection(username='snowman', password='frosty'):
    """
    Create a mock dataverse connection.

    Pass any credentials other than the default parameters and the connection
    will fail.
    """

    mock_connection = mock.create_autospec(DvnConnection)

    mock_connection.username = username
    mock_connection.password = password

    if username=='snowman' and password=='frosty':
        return mock_connection