
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from website.addons.base import StorageAddonBase
from website.oauth.models import ExternalProvider

class Evernote(ExternalProvider):
    pass

class EvernoteUserSettings(AddonUserSettingsBase):
    pass

class EvernoteNodeSettings(StorageAddonBase, AddonNodeSettingsBase):
    pass
