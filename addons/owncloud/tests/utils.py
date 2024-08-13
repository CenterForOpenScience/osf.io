from addons.base.tests.base import AddonTestCase, OAuthAddonTestCaseMixin
from addons.owncloud.models import NodeSettings, OwnCloudProvider, OwnCloudSerializer
from addons.owncloud.tests.factories import (
    OwnCloudAccountFactory,
    OwnCloudNodeSettingsFactory,
    OwnCloudUserSettingsFactory,
)


class OwnCloudAddonTestCaseBaseMixin:

    short_name = 'owncloud'
    full_name = 'OwnCloud'
    client = None  # Non-oauth add-on does not have client
    folder = {'path': '/Documents/', 'name': '/Documents', 'id': '/Documents/'}
    addon_short_name = 'owncloud'
    ADDON_SHORT_NAME = 'owncloud'
    Provider = OwnCloudProvider
    Serializer = OwnCloudSerializer
    ExternalAccountFactory = OwnCloudAccountFactory
    NodeSettingsFactory = OwnCloudNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = OwnCloudUserSettingsFactory


class OwnCloudBasicAuthAddonTestCase(OwnCloudAddonTestCaseBaseMixin, OAuthAddonTestCaseMixin, AddonTestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth = None
        self.external_account = None

    def set_user_settings(self, settings):
        super().set_user_settings(settings)

    def set_node_settings(self, settings):
        super().set_node_settings(settings)
