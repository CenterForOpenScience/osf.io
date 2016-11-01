from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.owncloud.models import OwnCloudProvider, NodeSettings
from addons.owncloud.tests.factories import (
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
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = OwnCloudUserSettingsFactory
    folder = {
        'path': '/Documents/',
        'name': '/Documents',
        'id': '/Documents/'
    }
