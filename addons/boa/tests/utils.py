from addons.base.tests.base import AddonTestCase, OAuthAddonTestCaseMixin
from addons.boa.models import BoaProvider, BoaSerializer, NodeSettings
from addons.boa.tests.factories import BoaAccountFactory, BoaNodeSettingsFactory, BoaUserSettingsFactory


class BoaAddonTestCaseBaseMixin:

    short_name = 'boa'
    full_name = 'Boa'
    client = None  # Non-oauth add-on does not have client
    folder = None  # Remote computing add-on does not have folder
    addon_short_name = 'boa'
    ADDON_SHORT_NAME = 'boa'
    Provider = BoaProvider
    Serializer = BoaSerializer
    ExternalAccountFactory = BoaAccountFactory
    NodeSettingsFactory = BoaNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = BoaUserSettingsFactory


class BoaBasicAuthAddonTestCase(BoaAddonTestCaseBaseMixin, OAuthAddonTestCaseMixin, AddonTestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth = None
        self.external_account = None

    def set_user_settings(self, settings):
        super().set_user_settings(settings)

    def set_node_settings(self, settings):
        super().set_node_settings(settings)
