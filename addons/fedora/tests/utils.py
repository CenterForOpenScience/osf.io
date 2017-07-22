from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.fedora.models import FedoraProvider
from addons.fedora.models import NodeSettings
from addons.fedora.tests.factories import (
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
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = FedoraUserSettingsFactory
    folder = {
        'path': '/Documents/',
        'name': '/Documents',
        'id': '/Documents/'
    }
