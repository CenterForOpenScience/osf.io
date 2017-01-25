from oauthlib.oauth2 import InvalidGrantError
from website.addons.base.serializer import StorageAddonSerializer
from website.util import api_url_for

class GoogleDriveSerializer(StorageAddonSerializer):

    addon_short_name = 'googledrive'

    def credentials_are_valid(self, user_settings, client):
        try:
            self.node_settings.fetch_access_token()
        except (InvalidGrantError, AttributeError):
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
            'config': node.api_url_for('googledrive_set_config'),
            'deauthorize': node.api_url_for('googledrive_deauthorize_node'),
            'importAuth': node.api_url_for('googledrive_import_auth'),
            'folders': node.api_url_for('googledrive_folder_list'),
            'accounts': node.api_url_for('googledrive_account_list')
        }

    @property
    def serialized_node_settings(self):
        result = super(GoogleDriveSerializer, self).serialized_node_settings
        valid_credentials = True
        if self.node_settings.external_account is not None:
            try:
                self.node_settings.fetch_access_token()
            except InvalidGrantError:
                valid_credentials = False
        result['validCredentials'] = valid_credentials
        return {'result': result}
