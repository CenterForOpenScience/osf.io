from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.boa.models import BoaProvider, NodeSettings
from addons.boa.tests.factories import (
    BoaAccountFactory, BoaNodeSettingsFactory,
    BoaUserSettingsFactory
)

class BoaAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    short_name = 'boa'
    full_name = 'Boa'
    ADDON_SHORT_NAME = 'boa'
    ExternalAccountFactory = BoaAccountFactory
    Provider = BoaProvider
    NodeSettingsFactory = BoaNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = BoaUserSettingsFactory
    folder = {
        'path': '/Documents/',
        'name': '/Documents',
        'id': '/Documents/'
    }
