from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.nextcloud.models import NextcloudProvider, NodeSettings
from addons.nextcloud.tests.factories import (
    NextcloudAccountFactory, NextcloudNodeSettingsFactory,
    NextcloudUserSettingsFactory
)

class NextcloudAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    short_name = 'nextcloud'
    full_name = 'Nextcloud'
    ADDON_SHORT_NAME = 'nextcloud'
    ExternalAccountFactory = NextcloudAccountFactory
    Provider = NextcloudProvider
    NodeSettingsFactory = NextcloudNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = NextcloudUserSettingsFactory
    folder = {
        'path': '/Documents/',
        'name': '/Documents',
        'id': '/Documents/'
    }
