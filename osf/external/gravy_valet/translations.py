import enum

import dataclasses
from dataclasses import asdict

from addons.bitbucket.apps import BitbucketAddonConfig
from addons.box.apps import BoxAddonAppConfig
from addons.dataverse.apps import DataverseAddonAppConfig
from addons.dropbox.apps import DropboxAddonAppConfig
from addons.figshare.apps import FigshareAddonAppConfig
from addons.github.apps import GitHubAddonConfig
from addons.gitlab.apps import GitLabAddonConfig
from addons.googledrive.apps import GoogleDriveAddonConfig
from addons.s3.apps import S3AddonAppConfig
from . import request_helpers as gv_requests


class _LegacyConfigsForWBKey(enum.Enum):
    """Mapping from a GV ExternalStorageService's waterbutler key to the legacy Addon config."""
    box = BoxAddonAppConfig
    bitbucket = BitbucketAddonConfig
    dataverse = DataverseAddonAppConfig
    dropbox = DropboxAddonAppConfig
    figshare = FigshareAddonAppConfig
    github = GitHubAddonConfig
    gitlab = GitLabAddonConfig
    googledrive = GoogleDriveAddonConfig
    s3 = S3AddonAppConfig


def make_ephemeral_user_settings(gv_account_data, requesting_user):
    service_wb_key = gv_account_data.get_included_attribute(
        include_path=('external_storage_service', ),
        attribute_name='wb_key'
    )
    legacy_config = _LegacyConfigsForWBKey[service_wb_key].value
    return EphemeralUserSettings(
        config=EphemeralAddonConfig.from_legacy_config(legacy_config),
        gv_data=gv_account_data,
        active_user=requesting_user,
    )


def make_ephemeral_node_settings(gv_addon_data, requested_resource, requesting_user):
    service_wb_key = gv_addon_data.get_included_attribute(
        include_path=('base_account', 'external_storage_service'),
        attribute_name='wb_key'
    )
    legacy_config = _LegacyConfigsForWBKey[service_wb_key].value
    return EphemeralNodeSettings(
        config=EphemeralAddonConfig.from_legacy_config(legacy_config),
        gv_data=gv_addon_data,
        configured_resource=requested_resource,
        active_user=requesting_user,
        wb_key=service_wb_key,
    )


@dataclasses.dataclass
class EphemeralAddonConfig:
    '''Minimalist dataclass for storing the actually used properties of an AddonConfig'''
    name: str
    label: str
    short_name: str
    full_name: str

    @property
    def has_hgrid_files(self):
        return True

    @classmethod
    def from_legacy_config(cls, legacy_config):
        return cls(
            name=legacy_config.name,
            label=legacy_config.label,
            full_name=legacy_config.full_name,
            short_name=legacy_config.short_name,
        )

    def to_json(self):
        return asdict(self)


@dataclasses.dataclass
class EphemeralNodeSettings:
    '''Minimalist dataclass for storing/translating the actually used properties of NodeSettings.'''
    config: EphemeralAddonConfig
    gv_data: gv_requests.JSONAPIResultEntry
    wb_key: str

    # These are needed in order to make further requests for credentials
    configured_resource: type  # Node
    active_user: type  # OSFUser

    # retrieved from WB on-demand and cached
    _credentials: dict = None
    _config: dict = None

    @property
    def short_name(self):
        return self.config.short_name

    @property
    def gv_id(self):
        return self.gv_data.resource_id

    @property
    def configured(self):
        return self.gv_data.get_included_attribute(
            include_path=['base_account'],
            attribute_name='credentials_available'
        )

    @property
    def deleted(self):
        return False

    @property
    def id(self):
        return self.gv_id

    @property
    def has_auth(self):
        return True

    @property
    def complete(self):
        return True

    def before_page_load(self, *args, **kwargs):
        pass

    @property
    def folder_id(self):
        return self.gv_data.get_attribute('root_folder')

    def serialize_waterbutler_credentials(self):
        # sufficient for most OAuth services, including Box
        # TODO: Define per-service translation (and/or common schemes)
        if self._credentials is None:
            self._fetch_wb_config()
        return self._credentials

    def serialize_waterbutler_settings(self):
        if self._config is None:
            self._fetch_wb_config()
        return self._config

    def _fetch_wb_config(self):
        result = gv_requests.get_waterbutler_config(
            gv_addon_pk=self.gv_data.resource_id,
            requested_resource=self.configured_resource,
            requesting_user=self.active_user
        )
        self._credentials = result.get_attribute('credentials')
        self._config = result.get_attribute('config')

    def create_waterbutler_log(self, *args, **kwargs):
        pass

    def save(self):
        pass

    def after_set_privacy(self, *args, **kwargs):
        pass


@dataclasses.dataclass
class EphemeralUserSettings:
    '''Minimalist dataclass for storing the actually used properties of UserSettings.'''
    config: EphemeralAddonConfig
    gv_data: gv_requests.JSONAPIResultEntry
    # This is needed to support making further requests
    active_user: type  # : OSFUser

    @property
    def short_name(self):
        return self.config.short_name

    @property
    def gv_id(self):
        return self.gv_data.resource_id

    @property
    def can_be_merged(self):
        return True
