from abc import ABC

from addons.base.tests.base import AddonTestCase
from addons.boa.models import BoaProvider, BoaSerializer, NodeSettings
from addons.boa.tests.factories import BoaAccountFactory, BoaNodeSettingsFactory, BoaUserSettingsFactory
from framework.auth import Auth


class BoaAddonTestCaseBaseMixin(ABC):

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


class BoaBasicAuthAddonTestCase(BoaAddonTestCaseBaseMixin, AddonTestCase):

    def __init__(self, *args, **kwargs):
        super(BoaBasicAuthAddonTestCase, self).__init__(*args, **kwargs)
        self.auth = None
        self.external_account = None

    def set_user_settings(self, settings):
        self.external_account = self.ExternalAccountFactory()
        self.external_account.save()
        self.user.external_accounts.add(self.external_account)
        self.user.save()
        self.auth = Auth(self.user)

    def set_node_settings(self, settings):
        self.user_settings.grant_oauth_access(self.project, self.external_account)
