import mock

from owncloud import Client as OwnCloudClient
from owncloud import FileInfo

from tests.factories import ExternalAccountFactory
from website.addons.base.testing import OAuthAddonTestCaseMixin, AddonTestCase
from website.addons.owncloud.model import OwnCloudProvider
from website.addons.owncloud.model import AddonOwnCloudNodeSettings
from website.addons.owncloud.tests.factories import (
    OwnCloudAccountFactory, OwnCloudNodeSettingsFactory,
    OwnCloudUserSettingsFactory
)

class OwnCloudAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    short_name = 'owncloud'
    full_name = 'OwnCloud'
    ADDON_SHORT_NAME = 'owncloud'
    ExternalAccountFactory = OwnCloudAccountFactory
    Provider = OwnCloudProvider
    NodeSettingsFactory = OwnCloudNodeSettingsFactory
    NodeSettingsClass = AddonOwnCloudNodeSettings
    UserSettingsFactory = OwnCloudUserSettingsFactory

    def set_node_settings(self, settings):
        super(OwnCloudAddonTestCase, self).set_node_settings(settings)
        settings.folder_name='/Documents'
        settings.external_account = self.external_account
        settings.save()

def create_mock_owncloud(host='qwe.rty', username='asd', password='fgh'):
    """
    Create a mock owncloud connection.

    Pass any credentials other than the default parameters and the connection
    will return none.
    """
    mock_owncloud = mock.create_autospec(OwnCloudClient)
    mock_owncloud.login.return_value = None
    mock_owncloud.logout.return_value = None
    mock_owncloud.list.return_value =[
        FileInfo('/Documents', file_type='dir', attributes=None),
        FileInfo('/Pictures', file_type='dir', attributes=None),
        FileInfo('/secrets.txt', file_type='txt', attributes=None),
    ]
    return mock_owncloud

def create_external_account(host='foo.bar.baz', username='doremi-abc-123',password='eh'):
    """Creates external account for Dataverse with fields populated the same
    way as `dataverse_add_user_account`"""

    return ExternalAccountFactory(
                provider='owncloud',
                provider_name = 'owncloud',
                display_name=username,
                oauth_key=host,
                oauth_secret=password,
                provider_id = host

    )
