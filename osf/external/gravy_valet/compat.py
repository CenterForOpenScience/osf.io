import enum

import dataclasses

from addons.box.apps import BoxAddonAppConfig
from osf.models import Node, OSFUser
from . import request_helpers as gv_requests


class _LegacyConfigsForImps(enum.Enum):
    """Mapping from a GravyValet StorageImp name to the Addon config."""
    box = BoxAddonAppConfig


def make_fake_node_settings(gv_data, requested_resource, requesting_user):
    service_wb_key = gv_data.get_nested_attribute(
        attribute_path=('base_account', 'external_storage_service'),
        attribute_name='wb_key'
    )
    legacy_config = _LegacyConfigsForImps(service_wb_key)
    return FakeNodeSettings(
        config=FakeAddonConfig.from_legacy_config(legacy_config),
        gv_id=gv_data.resource_id,
        folder_id=gv_data.get_attribute('configured_root_id'),
        configured_resource=requested_resource,
        active_user=requesting_user,
    )


@dataclasses.dataclass
class FakeAddonConfig:
    short_name: str

    @classmethod
    def from_legacy_config(legacy_config):
        return FakeAddonConfig(
            short_name=legacy_config.short_name
        )


@dataclasses.dataclass
class FakeNodeSettings:
    config: FakeAddonConfig
    folder_id: str
    gv_id: str
    configured_resource: Node
    active_user: OSFUser
    _storage_config: dict | None
    _credentials: dict | None

    @property
    def short_name(self):
        return self.config.short_name

    def serialize_waterbutler_credentials(self):
        if self._credentials is None:
            self._fetch_wb_config()
        return self._credentials

    def serialize_waterbutler_settings(self):
        # sufficient for box
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
class FakeUserSettings:
    config: FakeAddonConfig
    gv_id: str


def _get_service_name_from_gv_data(gv_data):
    return gv_data.get_included_attribute('base_account.external_storage_service.wb_key')

def _get_configured_folder_from_gv_data(gv_data):
    return gv_data.get_attribute('root_folder')
