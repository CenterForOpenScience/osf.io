import enum

import dataclasses

from addons.box.apps import BoxAddonAppConfig
from osf.models import Node, OSFUser
from . import request_helpers as gv_requests


class _LegacyConfigsForWBKey(enum.Enum):
    """Mapping from a GravyValet StorageImp name to the Addon config."""
    box = BoxAddonAppConfig


def make_ephemeral_node_settings(gv_addon_data, requested_resource, requesting_user):
    service_wb_key = gv_addon_data.get_included_attribute(
        attribute_path=('base_account', 'external_storage_service'),
        attribute_name='wb_key'
    )
    legacy_config = _LegacyConfigsForWBKey(service_wb_key)
    return EphemeralNodeSettings(
        config=EphemeralAddonConfig.from_legacy_config(legacy_config),
        gv_id=gv_addon_data.resource_id,
        folder_id=gv_addon_data.get_attribute('configured_root_id'),
        configured_resource=requested_resource,
        active_user=requesting_user,
    )

def make_ephemeral_user_settings(gv_account_data, requesting_user):
    service_wb_key = gv_account_data.get_included_attribute(
        attribute_path=('external_storage_service'),
        attribute_name='wb_key'
    )
    legacy_config = _LegacyConfigsForWBKey(service_wb_key)
    return EphemeralUserSettings(
        config=EphemeralAddonConfig.from_legacy_config(legacy_config),
        gv_id=gv_account_data.resource_id,
        active_user=requesting_user,
    )


@dataclasses.dataclass
class EphemeralAddonConfig:
    '''Minimalist dataclass for storing the actually used properties of an AddonConfig'''
    name: str
    label: str
    short_name: str
    full_name: str

    @classmethod
    def from_legacy_config(legacy_config):
        return EphemeralAddonConfig(
            name=legacy_config.name,
            label=legacy_config.label,
            full_name=legacy_config.full_name,
            short_name=legacy_config.short_name,
        )


@dataclasses.dataclass
class EphemeralNodeSettings:
    '''Minimalist dataclass for storing/translating the actually used properties of NodeSettings.'''
    config: EphemeralAddonConfig
    folder_id: str
    gv_id: str
    _storage_config: dict | None
    _credentials: dict | None

    # These are needed in order to make further requests for credentials
    configured_resource: Node
    active_user: OSFUser

    @property
    def short_name(self):
        return self.config.short_name

    def serialize_waterbutler_credentials(self):
        # sufficient for most OAuth services, including Box
        # TODO: Define per-service translation (or common schemes)
        if self._credentials is None:
            self._fetch_wb_config()
        return self._credentials

    def serialize_waterbutler_settings(self):
        # sufficient for Box
        # TODO: Define per-service translation (or common schemes)
        return {
            'folder': self.folder_id,
            'service': self.short_name,
        }

    def _fetch_wb_config(self):
        result = gv_requests.get_waterbutler_config(
            gv_addon_pk=self.gv_id,
            requested_resource=self.configured_resource,
            requesting_user=self.active_user
        )
        self._credentials = result.get_attribute('credentials')
        self._storage_config = result.get_attribute('settings')


@dataclasses.dataclass
class EphemeralUserSettings:
    '''Minimalist dataclass for storing the actually used properties of UserSettings.'''
    config: EphemeralAddonConfig
    gv_id: str
    # This is needed to support making further requests
    active_user: OSFUser

    @property
    def short_name(self):
        return self.config.short_name
