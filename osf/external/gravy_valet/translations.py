import dataclasses
from dataclasses import asdict, InitVar
from typing import TYPE_CHECKING

from framework.exceptions import HTTPError
from rest_framework import status as http_status

import markupsafe

from . import request_helpers as gv_requests

if TYPE_CHECKING:
    from osf.models import OSFUser, Node


def make_ephemeral_user_settings(gv_account_data, requesting_user):
    include_path = f'external_{gv_account_data.resource_type.split('-')[1]}_service'
    raw_config = gv_account_data.get_included_member(include_path)
    config = EphemeralAddonConfig(raw_config)
    return EphemeralUserSettings(
        config=config,
        gv_data=gv_account_data,
        active_user=requesting_user,
    )


def make_ephemeral_node_settings(gv_addon_data: gv_requests.JSONAPIResultEntry, requested_resource, requesting_user):
    addon_type = gv_addon_data.resource_type.split('-')[1]
    include_path = ('base_account', f'external_{addon_type}_service')
    config = EphemeralAddonConfig(gv_addon_data.get_included_member(*include_path))
    settings_class = get_settings_class(addon_type)
    return settings_class(
        config=config,
        gv_data=gv_addon_data,
        user_settings=make_ephemeral_user_settings(gv_addon_data.get_included_member('base_account'), requesting_user),
        configured_resource=requested_resource,
        active_user=requesting_user,
        wb_key=config.wb_key,
    )

_services = None

def get_external_services(requesting_user):
    global _services
    if _services:
        return _services
    _services = []
    for addon_type in gv_requests.AddonType:
        srv = [EphemeralAddonConfig(service) for service in gv_requests.iterate_gv_results(
            endpoint_url=gv_requests.ACCOUNT_EXTERNAL_SERVICE_ENDPOINT.format(addon_type=addon_type),
            requesting_user=requesting_user,
        )]
        _services += srv
    return _services

@dataclasses.dataclass
class EphemeralAddonConfig:
    """Minimalist dataclass for storing the actually used properties of an AddonConfig"""
    gv_data: InitVar[gv_requests.JSONAPIResultEntry]
    # name: str =  dataclasses.field(init=False, default=False)
    # label: str =  dataclasses.field(init=False, default=False)
    short_name: str = dataclasses.field(init=False)
    full_name: str = dataclasses.field(init=False)
    has_hgrid_files: bool = dataclasses.field(init=False, default=False)
    has_widget: bool = dataclasses.field(init=False, default=False)
    icon_url: str = dataclasses.field(init=False)
    wb_key: str = dataclasses.field(init=False)
    type: str = dataclasses.field(init=False)

    @property
    def added_default(self):
        return []

    def __post_init__(self, gv_data: gv_requests.JSONAPIResultEntry):
        self.short_name = gv_data.get_attribute('external_service_name')
        self.full_name = gv_data.get_attribute('display_name')
        self.has_hgrid_files = gv_data.resource_type == 'external-storage-services'
        self.has_widget = gv_data.resource_type == 'external-citation-services'
        self.icon_url = gv_data.get_attribute('icon_url')
        self.wb_key = gv_data.get_attribute('wb_key')
        self.type = gv_data.resource_type.split('-')[1]

    def to_json(self):
        return asdict(self)

@dataclasses.dataclass
class EphemeralUserSettings:
    """Minimalist dataclass for storing the actually used properties of UserSettings."""

    config: EphemeralAddonConfig
    gv_data: gv_requests.JSONAPIResultEntry
    # This is needed to support making further requests
    active_user: type  # : OSFUser
    _owner: 'OSFUser' = None
    owner_guid: str = dataclasses.field(init=False, default=None)

    def __post_init__(self):
        owner_url = self.gv_data.get_included_attribute(['account_owner'], 'user_uri')
        if owner_url:
            self.owner_guid = owner_url.split('/')[-1]

    @property
    def short_name(self):
        return self.config.short_name

    @property
    def owner(self) -> 'OSFUser':
        from osf.models import OSFUser
        if not self._owner:
            self._owner = OSFUser.load(self.owner_guid)
        return self._owner

    @property
    def gv_id(self):
        return self.gv_data.resource_id

    @property
    def can_be_merged(self):
        return True

    @property
    def public_id(self):
        return None

@dataclasses.dataclass
class EphemeralNodeSettings:
    """Minimalist dataclass for storing/translating the actually used properties of NodeSettings."""

    config: EphemeralAddonConfig
    user_settings: EphemeralUserSettings
    gv_data: gv_requests.JSONAPIResultEntry
    wb_key: str

    # These are needed in order to make further requests for credentials
    configured_resource: 'Node'
    # Active user is the user who initiates current operation, not node owner
    active_user: 'OSFUser'

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
            include_path=['base_account'], attribute_name='credentials_available'
        )

    @property
    def owner(self):
        return self.configured_resource

    @property
    def deleted(self):
        return False

    @property
    def id(self):
        return self.gv_id

    @property
    def _id(self):
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
            requesting_user=self.active_user,
            addon_type=self.gv_data.resource_type,
        )
        self._credentials = result.get_attribute('credentials')
        self._config = result.get_attribute('config')

    def create_waterbutler_log(self, *args, **kwargs):
        pass

    def save(self):
        pass

    def after_set_privacy(self, *args, **kwargs):
        pass

    def before_remove_contributor_message(self, node: 'Node', removed: 'OSFUser'):
        from addons.base.models import BaseOAuthNodeSettings
        return BaseOAuthNodeSettings.before_remove_contributor_message(self, node, removed)

    before_remove_contributor = before_remove_contributor_message

    def after_register(self, node, removed, auth):
        return None, None

    def after_remove_contributor(self, node, removed, auth):
        if self.user_settings.owner == removed:
            gv_requests.delete_addon(
                self.id,
                requesting_user=auth.user,
                requested_resource=node,
                addon_type=self.gv_data.resource_type
            )
            message = f'''
                 Because the {self.config.full_name} add-on for {markupsafe.escape(node.category_display)}
                 {markupsafe.escape(node.title)}" was authenticated by {markupsafe.escape(removed.fullname)},
                 authentication information has been deleted.
            '''
            if not auth or auth.user != removed:
                url = node.web_url_for('node_addons')
                message += f' You can re-authenticate on the <u><a href="{url}">addons</a></u> page.'
            return message

    def before_fork(self, node, user):
        from addons.base.models import BaseNodeSettings
        return BaseNodeSettings.before_fork(self, node, user)

    def after_fork(self, node: 'Node', fork, user: 'OSFUser', save=True):
        if user.id != self.active_user.id:
            # In this case we are not migrating addons to fork
            return
        json_data = self.gv_data.json()
        json_data['attributes']['authorized_resource_uri'] = fork.get_semantic_iri()
        json_data['relationships'].pop('authorized_resource')
        for relationship in json_data['relationships']:
            json_data['relationships'][relationship].pop('links')
        gv_requests.create_addon(
            requesting_user=user,
            requested_resource=fork,
            attributes=json_data['attributes'],
            relationships=json_data['relationships'],
            addon_type=self.gv_data.resource_type
        )

    def _get_fileobj_child_metadata(self, filenode, user, cookie=None, version=None):
        try:
            return super()._get_fileobj_child_metadata(filenode, user, cookie=cookie, version=version)
        except HTTPError as e:
            # The Dataverse API returns a 404 if the dataset has no published files
            if self.short_name == 'dataverse' and e.code == http_status.HTTP_404_NOT_FOUND and version == 'latest-published':
                return []
            raise

def get_settings_class(addon_type):
    if addon_type == gv_requests.AddonType.STORAGE:
        return _get_storage_settings_class()

    return EphemeralNodeSettings


def _get_storage_settings_class():
    if _StorageEphemeralNodeSettings is None:
        _initialize_ephemeral_storage_node_settings()
    return _StorageEphemeralNodeSettings


def _initialize_ephemeral_storage_node_settings():
    from addons.base.models import BaseStorageAddon

    global _StorageEphemeralNodeSettings

    class StorageEphemeralNodeSettings(EphemeralNodeSettings, BaseStorageAddon):
        pass

    _StorageEphemeralNodeSettings = StorageEphemeralNodeSettings


_StorageEphemeralNodeSettings = None
