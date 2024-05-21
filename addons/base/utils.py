import requests
import markupsafe
from os.path import basename
from website.settings import MFR_SERVER_URL

from website import settings


def get_mfr_url(target, provider_name):
    if hasattr(target, 'osfstorage_region') and provider_name == 'osfstorage':
        return target.osfstorage_region.mfr_url
    return MFR_SERVER_URL

def serialize_addon_config(config, user):
    lookup = config.template_lookup

    user_addon = user.get_addon(config.short_name)
    ret = {
        'addon_short_name': config.short_name,
        'addon_full_name': config.full_name,
        'node_settings_template': lookup.get_template(basename(config.node_settings_template)),
        'user_settings_template': lookup.get_template(basename(config.user_settings_template)),
        'is_enabled': user_addon is not None,
        'addon_icon_url': config.icon_url,
    }
    ret.update(user_addon.to_json(user) if user_addon else {})
    return ret

def get_addons_by_config_type(config_type, user):
    addons = [addon for addon in settings.ADDONS_AVAILABLE if config_type in addon.configs]
    return [serialize_addon_config(addon_config, user) for addon_config in sorted(addons, key=lambda cfg: cfg.full_name.lower())]

def format_last_known_metadata(auth, node, file, error_type):
    msg = """
    </div>"""  # None is default
    if error_type != 'FILE_SUSPENDED' and ((auth.user and node.is_contributor_or_group_member(auth.user)) or
            (auth.private_key and auth.private_key in node.private_link_keys_active)):
        last_meta = file.last_known_metadata
        last_seen = last_meta.get('last_seen', None)
        hashes = last_meta.get('hashes', None)
        path = last_meta.get('path', None)
        size = last_meta.get('size', None)
        parts = [
            """</br>This file was """ if last_seen or hashes or path or size else '',
            """last seen on {} UTC """.format(last_seen.strftime('%c')) if last_seen else '',
            """and found at path {} """.format(markupsafe.escape(path)) if last_seen and path else '',
            """last found at path {} """.format(markupsafe.escape(path)) if not last_seen and path else '',
            """with a file size of {} bytes""".format(size) if size and (last_seen or path) else '',
            """last seen with a file size of {} bytes""".format(size) if size and not (last_seen or path) else '',
            """.</br></br>""" if last_seen or hashes or path or size else '',
            """Hashes of last seen version:</br><p>{}</p>""".format(
                '</br>'.join(['{}: {}'.format(k, v) for k, v in hashes.items()])
            ) if hashes else '',  # TODO: Format better for UI
            msg
        ]
        return ''.join(parts)
    return msg


class GravyValetAddonAppConfig:
    class MockNodeSetting:
        def __init__(self, resource, auth, legacy_config):
            ...

    class MockUserSetting:
        def __init__(self, resource, auth, legacy_config):
            ...

    @staticmethod
    def get_configured_storage_addons_data(config_id, auth):
        resp = requests.get(
            settings.GV_NODE_ADDON_ENDPOINT.format(config_id=config_id),
        )
        return resp.json()

    def get_external_service_addon_data(self, auth):
        resp = requests.get(
            self.configured_storage_addons_data['data']['relationships']['external_storage_service']['links']['related'],
        )
        return resp.json()

    def __init__(self, resource, config_id, auth):
        self.config_id = config_id
        self.configured_storage_addons_data = self.get_configured_storage_addons_data(config_id, auth)
        # TODO: Names in GV must be exact matches?
        self.external_storage_service_data = self.get_external_service_addon_data(auth)
        self.addon_name = self.external_storage_service_data['data']['attributes']['name']
        self.legacy_config = settings.ADDONS_AVAILABLE_DICT[self.addon_name]
        self.resource = resource
        self.auth = auth
        self.FOLDER_SELECTED = self.legacy_config.FOLDER_SELECTED
        self.NODE_AUTHORIZED = self.legacy_config.NODE_DEAUTHORIZED
        self.NODE_DEAUTHORIZED = self.legacy_config.NODE_DEAUTHORIZED
        self.actions = self.legacy_config.actions

    @property
    def node_settings(self):
        return self.MockNodeSetting(self.resource, self.auth, self.legacy_config)

    @property
    def user_settings(self):
        return self.MockUserSetting(self.resource, self.auth, self.legacy_config)

    @property
    def configured(self):
        return True
