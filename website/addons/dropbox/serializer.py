from dropbox.rest import ErrorResponse

from website.util import api_url_for
from website.addons.base.serializer import StorageAddonSerializer
from website.addons.dropbox.client import get_client_from_user_settings

class DropboxSerializer(StorageAddonSerializer):

    addon_short_name = 'dropbox'

    def credentials_are_valid(self, user_settings, client):
        if user_settings:
            client = client or get_client_from_user_settings(user_settings)
            try:
                client.account_info()
            except (ValueError, IndexError, ErrorResponse):
                return False
        return True

    def serialized_folder(self, node_settings):
        path = node_settings.folder
        return {
            'name': path if path != '/' else '/ (Full Dropbox)',
            'path': path
        }

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner

        return {
            'auth': api_url_for('oauth_connect',
                                service_name='dropbox'),
            'importAuth': node.api_url_for('dropbox_import_user_auth'),
            'files': node.web_url_for('collect_file_trees'),
            'folders': node.api_url_for('dropbox_get_folders'),
            'config': node.api_url_for('dropbox_config_put'),
            'emails': node.api_url_for('dropbox_get_share_emails'),
            'deauthorize': node.api_url_for('dropbox_remove_user_auth'),
            'accounts': node.api_url_for('dropbox_user_config_get'),
        }
