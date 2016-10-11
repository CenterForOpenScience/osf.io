import logging

from addons.base.models import AddonNodeSettingsBase, StorageAddonBase

logger = logging.getLogger(__name__)

class OsfStorageNodeSettings(StorageAddonBase, AddonNodeSettingsBase):
    pass
