import mock
from website.addons.dataverse.dvn.connection import DvnConnection


def create_mock_connection(username='snowman', password='frosty'):

    mock_connection = mock.create_autospec(DvnConnection)

    mock_connection.username = username
    mock_connection.password = password

    if username=='snowman' and password=='frosty':
        return mock_connection