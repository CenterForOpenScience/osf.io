
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase
from website.addons.dmptool import (settings, utils)
from website.addons.dmptool.serializer import DmptoolSerializer
from website.oauth.models import ExternalProvider

from modularodm import fields

import logging
logger = logging.getLogger(__name__)

class Dmptool(ExternalProvider):
    """
    First cut at the Dmptool provider

    """
    name = 'DMPTool'
    short_name = 'dmptool'


class DmptoolUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = Dmptool
    serializer = DmptoolSerializer


class DmptoolNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = Dmptool
    serializer = DmptoolSerializer

