from dropbox.rest import ErrorResponse
from dropbox.client import DropboxClient


from website.util import api_url_for
from website.addons.base.serializer import StorageAddonSerializer

class FedoraSerializer(StorageAddonSerializer):

    addon_short_name = 'fedora'

    def credentials_are_valid(self, user_settings, client):
        if user_settings:
            client = client or DropboxClient(user_settings.external_accounts[0].oauth_key)
            try:
                client.account_info()
            except (ValueError, IndexError, ErrorResponse):
                return False
        return True

    def serialized_folder(self, node_settings):
        path = node_settings.folder
        return {
            'name': path if path != '/' else '/ (Full Fedora)',
            'path': path
        }

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner

        return {
            'auth': api_url_for('oauth_connect',
                                service_name='fedora'),
            'importAuth': node.api_url_for('fedora_import_auth'),
            'files': node.web_url_for('collect_file_trees'),
            'folders': node.api_url_for('fedora_folder_list'),
            'config': node.api_url_for('fedora_set_config'),
            'deauthorize': node.api_url_for('fedora_deauthorize_node'),
            'accounts': node.api_url_for('fedora_account_list'),
        }
