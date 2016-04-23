
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase
from website.addons.dmptool import (settings, utils)
from website.addons.dmptool.serializer import DmptoolSerializer

from modularodm import fields

import logging
logger = logging.getLogger(__name__)


class DmptoolProvider(object):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'DMPTool'
    short_name = 'dmptool'
    serializer = DmptoolSerializer

    def __init__(self, account=None):
        super(DmptoolProvider, self).__init__()
        # provide an unauthenticated session by default
        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.provider_id if self.account else 'anonymous'
        )

class DmptoolUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = DmptoolProvider
    serializer = DmptoolSerializer


class DmptoolNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = DmptoolProvider
    serializer = DmptoolSerializer

