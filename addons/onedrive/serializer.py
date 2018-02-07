from oauthlib.oauth2 import InvalidGrantError

from website.util import api_url_for
from addons.base.serializer import StorageAddonSerializer


class OneDriveSerializer(StorageAddonSerializer):

    addon_short_name = 'onedrive'

    def credentials_are_valid(self, user_settings, client):
        try:
            self.node_settings.fetch_access_token()
        except (InvalidGrantError, AttributeError):
            return False
        return True

    def serialized_folder(self, node_settings):
        return {
            'name': node_settings.folder_name,
            'path': node_settings.folder_path,
        }

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner

        return {
            'auth': api_url_for('oauth_connect', service_name='onedrive'),
            'importAuth': node.api_url_for('onedrive_import_auth'),
            'files': node.web_url_for('collect_file_trees'),
            'folders': node.api_url_for('onedrive_folder_list'),
            'config': node.api_url_for('onedrive_set_config'),
            'deauthorize': node.api_url_for('onedrive_deauthorize_node'),
            'accounts': node.api_url_for('onedrive_account_list'),
        }
