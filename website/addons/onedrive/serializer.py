import logging

from website.addons.base.serializer import OAuthAddonSerializer

from website.util import api_url_for, web_url_for

# from OneDriveSDK
import onedrivesdk
from onedrivesdk.helpers import GetAuthCodeServer


logger = logging.getLogger(__name__)

logging.getLogger('onedrive1').setLevel(logging.WARNING)

class OneDriveSerializer(OAuthAddonSerializer):

    def credentials_owner(self, user_settings=None):
        return user_settings.owner or self.user_settings.owner

    @property
    def user_is_owner(self):
        if self.user_settings is None or self.node_settings is None:
            return False

        user_accounts = self.user_settings.external_accounts
        return bool(
            (
                self.node_settings.has_auth and
                (self.node_settings.external_account in user_accounts)
            ) or len(user_accounts)
        )

    @property
    def serialized_urls(self):
        
        logger.error('serialized_urls-1')
        
        ret = self.addon_serialized_urls
        ret.update({'settings': web_url_for('user_addons')})
        return ret

    @property
    def addon_serialized_urls(self):
        logger.error('addon_serialized_urls-1')
        node = self.node_settings.owner
        
        return {
            #'auth': api_url_for('oauth_connect',
             #                   service_name='onedrive'),
            'importAuth': node.api_url_for('onedrive_add_user_auth'),
            'files': node.web_url_for('collect_file_trees'),
            'folders': node.api_url_for('onedrive_folder_list'),
            'config': node.api_url_for('onedrive_set_config'),
            #'emails': node.api_url_for('onedrive_get_share_emails'),
            #'share': 'https://app.onedrive.com/files/0/f/{0}'.format(self.node_settings.folder_id),
            'deauthorize': node.api_url_for('onedrive_remove_user_auth'),
            'accounts': node.api_url_for('onedrive_get_user_settings'),
        }

    def serialize_settings(self, node_settings, current_user, client=None):
        """View helper that returns a dictionary representation of a
        OneDriveNodeSettings record. Provides the return value for the
        onedrive config endpoints.
        """
        
        logger.error('addon_serialized_settings-1')
        #TODO: review onedrive serilaized settings to determine if we need to add more
        valid_credentials = True
        user_settings = node_settings.user_settings
        self.node_settings = node_settings
        current_user_settings = current_user.get_addon('onedrive')
        user_is_owner = user_settings is not None and user_settings.owner == current_user

#        if user_settings:
#            try:
#                client = client or OneDriveClient(user_settings.external_accounts[0].oauth_key)
#                client.get_user_info()
#            except (OneDriveClientException, IndexError):
#                valid_credentials = False

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
                #path = node_settings.fetch_full_folder_path()
                path = node_settings.folder_id
                result['folder'] = {
                    'path': path,
                    'name': path.replace('All Files', '', 1) if path != 'All Files' else '/ (Full OneDrive)'
                }
        return result
