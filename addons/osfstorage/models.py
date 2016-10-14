import logging

from addons.base.models import BaseNodeSettings, BaseStorageAddon

logger = logging.getLogger(__name__)

class NodeSettings(BaseStorageAddon, BaseNodeSettings):
    pass
