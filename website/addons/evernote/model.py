
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from website.addons.base import StorageAddonBase

class EvernoteUserSettings(AddonUserSettingsBase):
    pass

class EvernoteNodeSettings(StorageAddonBase, AddonNodeSettingsBase):
    pass