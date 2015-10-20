from website.util import api_url_for, web_url_for

from website.addons.base.serializer import OAuthAddonSerializer

from website.addons.dropbox.client import get_client_from_user_settings

class DropboxSerializer(OAuthAddonSerializer):

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
            'deauthorize': node.api_url_for('dropbox_oauth_delete_user'),
            'accounts': node.api_url_for('dropbox_user_config_get'),
            'share': None
        }

    def serialize_settings(self, node_settings, current_user, client=None):
        """View helper that returns a dictionary representation of a
        BoxNodeSettings record. Provides the return value for the
        box config endpoints.
        """
        valid_credentials = True
        user_settings = node_settings.user_settings
        self.node_settings = node_settings
        current_user_settings = current_user.get_addon('box')
        user_is_owner = user_settings is not None and user_settings.owner == current_user

        if user_settings:
            try:
                client = client or get_client_from_user_settings(user_settings)
                client.get_user_info()
            except (ValueError, IndexError):
                valid_credentials = False

        result = {
            'userIsOwner': user_is_owner,
            'nodeHasAuth': node_settings.has_auth,
            'urls': self.addon_serialized_urls,
            'validCredentials': valid_credentials,
            'userHasAuth': current_user_settings is not None and current_user_settings.has_auth,
        }

        if node_settings.has_auth:
            # Add owner's profile URL
            result['urls']['owner'] = web_url_for(
                'profile_view_id',
                uid=user_settings.owner._id
            )
            result['ownerName'] = user_settings.owner.fullname
            # Show available folders
            # path = node_settings.folder

            if node_settings.folder_id is None:
                result['folder'] = {'name': None, 'path': None}
            elif valid_credentials:
                path = node_settings.fetch_full_folder_path()

                result['folder'] = {
                    'path': path,
                    'name': path.replace('All Files', '', 1) if path != 'All Files' else '/ (Full Dropbox)'
                }
        return result
