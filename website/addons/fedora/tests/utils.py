from website.addons.base.testing import OAuthAddonTestCaseMixin, AddonTestCase
from website.addons.fedora.model import FedoraProvider
from website.addons.fedora.model import AddonFedoraNodeSettings
from website.addons.fedora.tests.factories import (
    FedoraAccountFactory, FedoraNodeSettingsFactory,
    FedoraUserSettingsFactory
)

class FedoraAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    short_name = 'fedora'
    full_name = 'Fedora'
    ADDON_SHORT_NAME = 'fedora'
    ExternalAccountFactory = FedoraAccountFactory
    Provider = FedoraProvider
    NodeSettingsFactory = FedoraNodeSettingsFactory
    NodeSettingsClass = AddonFedoraNodeSettings
    UserSettingsFactory = FedoraUserSettingsFactory
    folder = {
        'path': '/Documents/',
        'name': '/Documents',
        'id': '/Documents/'
    }
