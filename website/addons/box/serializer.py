from website.addons.base.serializer import StorageAddonSerializer

from website.util import api_url_for

from box.client import BoxClient, BoxClientException


class BoxSerializer(StorageAddonSerializer):

    addon_short_name = 'box'

    def credentials_are_valid(self, user_settings, client):
        if user_settings:
            client = client or BoxClient(user_settings.external_accounts[0].oauth_key)
            try:
                client.get_user_info()
            except (BoxClientException, IndexError):
                return False
        return True

    def serialized_folder(self, node_settings):
        path = node_settings.fetch_full_folder_path()
        return {
            'path': path,
            'name': path.replace('All Files', '', 1) if path != 'All Files' else '/ (Full Box)'
        }

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner

        return {
            'auth': api_url_for('oauth_connect',
                                service_name='box'),
            'importAuth': node.api_url_for('box_import_auth'),
            'files': node.web_url_for('collect_file_trees'),
            'folders': node.api_url_for('box_folder_list'),
            'config': node.api_url_for('box_set_config'),
            'deauthorize': node.api_url_for('box_deauthorize_node'),
            'accounts': node.api_url_for('box_account_list'),
        }
