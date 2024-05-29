import requests
import markupsafe
from os.path import basename
from website.settings import MFR_SERVER_URL


from api.caching import settings as cache_settings
from api.caching.utils import legacy_addon_cache

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

    @staticmethod
    def get_configured_storage_addons_data(config_id, user):
        from osf.external.gravy_valet import auth_helpers as gv_auth
        url = settings.GV_NODE_ADDON_ENDPOINT.format(config_id=config_id)

        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=url,
            request_method='GET',
            requesting_user=user,
        )

        resp = requests.get(url, headers=auth_headers)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def get_authorized_storage_account(config_id, user):
        from osf.external.gravy_valet import auth_helpers as gv_auth
        url = settings.GV_USER_ADDON_ENDPOINT.format(config_id=config_id)
        auth_headers = gv_auth.make_gravy_valet_hmac_headers(
            request_url=url,
            request_method='GET',
            requesting_user=user,
        )

        resp = requests.get(url, headers=auth_headers)
        resp.raise_for_status()
        return resp.json()

    def cache_config_id_translation(self):
        """
        Cache what legacy addon name corresponds to which config ids.
        """

        key = cache_settings.LEGACY_ADDON_KEY.format(target_id=self.config_id)
        legacy_addon_cache.set(key, self.addon_name, settings.STORAGE_USAGE_CACHE_TIMEOUT)

    def __init__(self, resource, config_id, user):
        self.resource = resource
        self.user = user
        self.FOLDER_SELECTED = self.legacy_app_config.FOLDER_SELECTED
        self.NODE_AUTHORIZED = self.legacy_app_config.NODE_DEAUTHORIZED
        self.NODE_DEAUTHORIZED = self.legacy_app_config.NODE_DEAUTHORIZED
        self.actions = self.legacy_app_config.actions

        from osf.models import OSFUser, AbstractNode
        if isinstance(resource, AbstractNode):
            self.gv_data = self.get_configured_storage_addons_data(config_id, user)
        elif isinstance(resource, OSFUser):
            self.gv_data = self.get_authorized_storage_account(config_id, user)
        else:
            raise NotImplementedError()

        # TODO: Names in GV must be exact matches?
        self.addon_name = self.gv_data['data']['embeds']['external_storage_service']['attributes']['name']
        self.cache_config_id_translation()
        self.legacy_app_config = settings.ADDONS_AVAILABLE_DICT[self.addon_name]


    @property
    def config(self):
        return self.legacy_app_config

    @property
    def configured(self):
        return True

    @property
    def config_id(self):
        return self.gv_data.config_id
