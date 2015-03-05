from dropbox.rest import ErrorResponse

from website.util import web_url_for

from website.addons.base.serializer import StorageAddonSerializer

from website.addons.dropbox.client import get_client_from_user_settings
from website.addons.dropbox.utils import get_share_folder_uri

class DropboxSerializer(StorageAddonSerializer):

    @property
    def serialized_urls(self):
        node = self.addon_node_settings.owner
        if self.addon_node_settings.folder and self.addon_node_settings.folder != '/':
            # The link to share a the folder with other Dropbox users
            share_url = get_share_folder_uri(self.addon_node_settings.folder)
        else:
            share_url = None

        urls = {
            'config': node.api_url_for('dropbox_config_put'),
            'deauthorize': node.api_url_for('dropbox_deauthorize'),
            'auth': node.api_url_for('dropbox_oauth_start'),
            'importAuth': node.api_url_for('dropbox_import_user_auth'),
            'files': node.web_url_for('collect_file_trees'),
            # Endpoint for fetching only folders (including root)
            'folders': node.api_url_for('dropbox_hgrid_data_contents', root=1),
            'share': share_url,
            'emails': node.api_url_for('dropbox_get_share_emails'),
            'settings': web_url_for('user_addons')
        }
        return urls

    @property
    def has_valid_credentials(self):
        user_settings = self.addon_node_settings.user_settings

        valid_credentials = True
        if user_settings:
            try:
                client = get_client_from_user_settings(user_settings)
                client.account_info()
            except ErrorResponse as error:
                if error.status == 401:
                    valid_credentials = False
        else:
            valid_credentials = False
        return valid_credentials

    @property
    def node_has_auth(self):
        return self.addon_node_settings.has_auth

    @property
    def user_has_auth(self):
        current_user_settings = self.user.get_addon('dropbox')
        return current_user_settings is not None and current_user_settings.has_auth

    @property
    def user_is_owner(self):
        addon_user_settings = self.addon_node_settings.user_settings
        return addon_user_settings is not None and (
            addon_user_settings.owner._primary_key == self.user._primary_key
        )

    @property
    def credentials_owner(self):
        addon_user_settings = self.addon_node_settings.user_settings
        return None if not addon_user_settings else addon_user_settings.owner

    @property
    def serialized_folder(self):
        path = self.addon_node_settings.folder
        if path is None:
            return {'name': None, 'path': None}
        else:
            return {
                'name': path if path != '/' else '/ (Full Dropbox)',
                'path': path
            }
