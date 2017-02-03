import logging

from website.addons.base.serializer import OAuthAddonSerializer

from website.util import api_url_for

from website.addons.onedrive.client import OneDriveClient

logger = logging.getLogger(__name__)


class OneDriveSerializer(OAuthAddonSerializer):

    addon_short_name = 'onedrive'

    def credentials_are_valid(self, user_settings, client):
        if not user_settings:
            return False
        try:
            client = client or OneDriveClient(user_settings.external_accounts[0].oauth_key)
            client.get_user_info()
        except (IndexError):
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
            'auth': api_url_for('oauth_connect',
                                service_name='onedrive'),
            'importAuth': node.api_url_for('onedrive_add_user_auth'),
            'files': node.web_url_for('collect_file_trees'),
            'folders': node.api_url_for('onedrive_folder_list'),
            'config': node.api_url_for('onedrive_set_config'),
            'deauthorize': node.api_url_for('onedrive_remove_user_auth'),
            'accounts': node.api_url_for('onedrive_get_user_settings'),
        }
