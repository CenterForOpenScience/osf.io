from addons.base.serializer import StorageAddonSerializer

from addons.figshare.client import FigshareClient
from website.util import api_url_for, web_url_for

class FigshareSerializer(StorageAddonSerializer):

    addon_short_name = 'figshare'

    def credentials_are_valid(self, user_settings, client):
        if user_settings:
            client = client or FigshareClient.from_account(user_settings.external_accounts[0])
            try:
                client.userinfo()
            except:
                return False
            else:
                return True
        return False

    def serialized_folder(self, node_settings):
        return {
            'path': node_settings.folder_id,
            'name': node_settings.folder_name
        }

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        user_settings = self.node_settings.user_settings or self.user_settings

        result = {
            'auth': api_url_for('oauth_connect', service_name='figshare'),
            'accounts': node.api_url_for('figshare_account_list'),
            'importAuth': node.api_url_for('figshare_import_auth'),
            'deauthorize': node.api_url_for('figshare_deauthorize_node'),
            'folders': node.api_url_for('figshare_folder_list'),
            'config': node.api_url_for('figshare_set_config'),
            'files': node.web_url_for('collect_file_trees'),
        }
        if user_settings:
            result['owner'] = web_url_for('profile_view_id',
                uid=user_settings.owner._id)
        return result
