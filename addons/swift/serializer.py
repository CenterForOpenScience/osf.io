from website.util import web_url_for
from addons.base.serializer import StorageAddonSerializer
from addons.swift import utils

from addons.swift.provider import SwiftProvider


class SwiftSerializer(StorageAddonSerializer):
    addon_short_name = 'swift'

    REQUIRED_URLS = []

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        user_settings = self.node_settings.user_settings or self.user_settings

        result = {
            'accounts': node.api_url_for('swift_account_list'),
            'createContainer': node.api_url_for('swift_create_container'),
            'importAuth': node.api_url_for('swift_import_auth'),
            'create': node.api_url_for('swift_add_user_account'),
            'deauthorize': node.api_url_for('swift_deauthorize_node'),
            'folders': node.api_url_for('swift_folder_list'),
            'config': node.api_url_for('swift_set_config'),
            'files': node.web_url_for('collect_file_trees'),
        }
        if user_settings:
            result['owner'] = web_url_for('profile_view_id',
                uid=user_settings.owner._id)
        return result

    def serialized_folder(self, node_settings):
        return {
            'path': node_settings.folder_id,
            'name': node_settings.folder_name
        }

    def credentials_are_valid(self, user_settings, client=None):
        if user_settings:
            for account in user_settings.external_accounts:
                provider = SwiftProvider(account)
                if utils.can_list(provider.auth_version,
                                  provider.auth_url, provider.username,
                                  provider.user_domain_name,
                                  provider.password, provider.tenant_name,
                                  provider.project_domain_name):
                    return True
        return False
