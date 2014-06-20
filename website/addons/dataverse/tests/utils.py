import mock

from webtest_plus import TestApp
from dataverse import Connection, Dataverse, Study, DataverseFile

import website
from website.addons.base.testing import AddonTestCase

app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)


class DataverseAddonTestCase(AddonTestCase):
    ADDON_SHORT_NAME = 'dataverse'

    def create_app(self):
        return TestApp(app)

    def set_user_settings(self, settings):
        settings.dataverse_username = 'snowman'
        settings.dataverse_password = 'frosty'

    def set_node_settings(self, settings):
        settings.dataverse_alias = 'ALIAS2'
        settings.dataverse = 'Example 2'
        settings.study_hdl = 'doi:12.3456/DVN/00001'
        settings.study = 'Example (DVN/00001)'


def create_mock_connection(username='snowman', password='frosty'):
    """
    Create a mock dataverse connection.

    Pass any credentials other than the default parameters and the connection
    will fail.
    """

    mock_connection = mock.create_autospec(Connection)

    mock_connection.username = username
    mock_connection.password = password
    mock_connection.status = 200

    mock_connection.get_dataverses.return_value = [
        create_mock_dataverse('Example 1'),
        create_mock_dataverse('Example 2'),
        create_mock_dataverse('Example 3')
    ]

    def _get_dataverse(alias):
        return next((
            dataverse for dataverse in mock_connection.get_dataverses()
            if alias is not None and dataverse.title[-1] == alias[-1]), None
        )

    mock_connection.get_dataverse = mock.MagicMock(
        side_effect=_get_dataverse
    )
    mock_connection.get_dataverse.return_value = create_mock_dataverse()

    if username == 'snowman' and password == 'frosty':
        return mock_connection


def create_mock_dataverse(title='Example Dataverse 0'):

    mock_dataverse = mock.create_autospec(Dataverse)

    type(mock_dataverse).title = mock.PropertyMock(return_value=title)
    type(mock_dataverse).is_released = mock.PropertyMock(return_value=True)
    type(mock_dataverse).alias = mock.PropertyMock(
        return_value='ALIAS{}'.format(title[-1])
    )

    mock_dataverse.get_studies.return_value = [
        create_mock_study('DVN/00001'),
        create_mock_study('DVN/00002'),
        create_mock_study('DVN/00003')
    ]

    def _get_study_by_doi(hdl):
        return next((
            study for study in mock_dataverse.get_studies()
            if study.doi == hdl), None
        )

    mock_dataverse.get_study_by_doi = mock.MagicMock(
        side_effect=_get_study_by_doi
    )

    return mock_dataverse


def create_mock_study(id='DVN/12345'):
    mock_study = mock.create_autospec(Study)

    mock_study.citation = 'Example Citation for {0}'.format(id)
    mock_study.title = 'Example ({0})'.format(id)
    mock_study.doi = 'doi:12.3456/{0}'.format(id)
    mock_study.get_state.return_value = 'DRAFT'

    def _create_file(name, released=False):
        return create_mock_released_file() if released else create_mock_draft_file()

    def _create_files(released=False):
        return [_create_file('name.txt', released)]

    mock_study.get_files = mock.MagicMock(side_effect=_create_files)
    mock_study.get_file = mock.MagicMock(side_effect=_create_file)
    mock_study.get_file_by_id = mock.MagicMock(side_effect=_create_file)

    # Fail if not given a valid ID
    if 'DVN' in id:
        return mock_study

def create_mock_draft_file(id='54321'):
    mock_file = mock.create_autospec(DataverseFile)

    mock_file.name = 'file.txt'
    mock_file.id = id
    mock_file.is_released = False

    return mock_file

def create_mock_released_file(id='54321'):
    mock_file = mock.create_autospec(DataverseFile)

    mock_file.name = 'released.txt'
    mock_file.id = id
    mock_file.is_released = True

    return mock_file

mock_responses = {
    'contents': {
        u'kind': u'item',
        u'name': u'file.txt',
        u'ext': u'.txt',
        u'file_id': u'54321',
        u'urls': {u'download': u'/project/xxxxx/dataverse/file/54321/download/',
                 u'delete': u'/api/v1/project/xxxxx/dataverse/file/54321/',
                 u'view': u'/project/xxxxx/dataverse/file/54321/'},
        u'permissions': {u'edit': False, u'view': True},
        u'addon': u'dataverse'
    }
}