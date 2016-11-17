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
    folder = {
        'path': '/Documents/',
        'name': '/Documents',
        'id': '/Documents/'
    }
