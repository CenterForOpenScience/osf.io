from website.addons.base.serializer import OAuthAddonSerializer
from website.addons.googledrive.exceptions import ExpiredAuthError


class GoogleDriveSerializer(OAuthAddonSerializer):

    @property
    def addon_serialized_urls(self):

        node = self.node_settings.owner
        return {
            'files': node.web_url_for('collect_file_trees'),
            'config': node.api_url_for('googledrive_config_put'),
            'deauthorize': node.api_url_for('googledrive_remove_user_auth'),
            'importAuth': node.api_url_for('googledrive_import_user_auth'),
            'folders': node.api_url_for('googledrive_folders'),
            'accounts': node.api_url_for('list_googledrive_user_accounts')
        }

    @property
    def serialized_node_settings(self):
        result = super(GoogleDriveSerializer, self).serialized_node_settings
        valid_credentials = True
        if self.node_settings.external_account is not None:
            try:
                self.node_settings.fetch_access_token()
            except ExpiredAuthError:
                valid_credentials = False
        result['validCredentials'] = valid_credentials
        return {'result': result}
