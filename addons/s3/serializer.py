from website.util import web_url_for
from addons.base.serializer import StorageAddonSerializer
from addons.s3 import utils

class S3Serializer(StorageAddonSerializer):
    addon_short_name = 's3'

    REQUIRED_URLS = []

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        user_settings = self.node_settings.user_settings or self.user_settings

        result = {
            'accounts': node.api_url_for('s3_account_list'),
            'createBucket': node.api_url_for('create_bucket'),
            'putHost': node.api_url_for('put_host'),
            'importAuth': node.api_url_for('s3_import_auth'),
            'create': node.api_url_for('s3_add_user_account'),
            'deauthorize': node.api_url_for('s3_deauthorize_node'),
            'folders': node.api_url_for('s3_folder_list'),
            'config': node.api_url_for('s3_set_config'),
            'files': node.web_url_for('collect_file_trees'),
        }
        if user_settings:
            result['owner'] = web_url_for('profile_view_id',
                uid=user_settings.owner._id)
        return result

    def serialize_settings(self, node_settings, current_user, client=None):
        user_settings = node_settings.user_settings
        self.node_settings = node_settings
        current_user_settings = current_user.get_addon(self.addon_short_name)
        user_is_owner = user_settings is not None and user_settings.owner == current_user

        valid_credentials = self.credentials_are_valid(user_settings, client)

        result = {
            'userIsOwner': user_is_owner,
            'nodeHasAuth': node_settings.has_auth,
            'urls': self.serialized_urls,
            'validCredentials': valid_credentials,
            'userHasAuth': current_user_settings is not None and current_user_settings.has_auth,
            'providerHost': node_settings.host
        }

        if node_settings.has_auth:
            # Add owner's profile URL
            result['urls']['owner'] = web_url_for(
                'profile_view_id',
                uid=user_settings.owner._id
            )
            result['ownerName'] = user_settings.owner.fullname
            # Show available folders
            if node_settings.folder_id is None:
                result['folder'] = {'name': None, 'path': None}
            elif valid_credentials:
                result['folder'] = self.serialized_folder(node_settings)
        return result

    def serialized_folder(self, node_settings):
        return {
            'path': node_settings.folder_id,
            'name': node_settings.folder_name
        }

    def credentials_are_valid(self, user_settings, client=None):
        if user_settings:
            for account in user_settings.external_accounts.all():
                if utils.can_list(
                    account.host,
                    account.port,
                    account.oauth_key,
                    account.oauth_secret,
                    account.encrypted
                ):
                    return True
        return False
