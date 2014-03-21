import mock
from website.addons.dataverse.dvn.connection import DvnConnection
from website.addons.dataverse.dvn.dataverse import Dataverse
from website.addons.dataverse.dvn.study import Study


def create_mock_connection(username='snowman', password='frosty'):
    """
    Create a mock dataverse connection.

    Pass any credentials other than the default parameters and the connection
    will fail.
    """

    mock_connection = mock.create_autospec(DvnConnection)

    mock_connection.username = username
    mock_connection.password = password

    mock_connection.get_dataverses.return_value = [create_mock_dataverse(),
                                                   create_mock_dataverse()]

    if username=='snowman' and password=='frosty':
        return mock_connection


def create_mock_dataverse(title='Dataverse 1'):

    mock_dataverse = mock.create_autospec(Dataverse)

    type(mock_dataverse).title = mock.PropertyMock(return_value=title)
    mock_dataverse.get_studies.return_value = [create_mock_study()]
    mock_dataverse.get_study_by_hdl.return_value = create_mock_study()

    return mock_dataverse


def create_mock_study(id='DVN/12345'):
    mock_study = mock.create_autospec(Study)

    mock_study.get_id.return_value = id
    mock_study.get_title.return_value = 'Example Study'
    mock_study.doi.return_value = 'doi:12.3456/{0}'.format(id)

    return mock_study
