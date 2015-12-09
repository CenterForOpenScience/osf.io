from website.util import api_url_for

from website.addons.base.serializer import StorageAddonSerializer
from website.addons.googledrive.exceptions import ExpiredAuthError


class GoogleDriveSerializer(StorageAddonSerializer):

    addon_short_name = 'googledrive'

    def credentials_are_valid(self, user_settings, client):
        try:
            self.node_settings.fetch_access_token()
        except (ExpiredAuthError, AttributeError):
            return False
        return True

    def serialized_folder(self, node_settings):
        return {
            'name': node_settings.folder_name,
            'path': node_settings.folder_path
        }

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        return {
            'auth': api_url_for('oauth_connect',
                                service_name='googledrive'),
            'files': node.web_url_for('collect_file_trees'),
            'config': node.api_url_for('googledrive_config_put'),
            'deauthorize': node.api_url_for('googledrive_remove_user_auth'),
            'importAuth': node.api_url_for('googledrive_import_user_auth'),
            'folders': node.api_url_for('googledrive_folders'),
            'accounts': node.api_url_for('list_googledrive_user_accounts')
        }
