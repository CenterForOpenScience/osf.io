from website.util import web_url_for
from addons.base.serializer import StorageAddonSerializer
from addons.s3compatb3 import utils

class S3CompatB3Serializer(StorageAddonSerializer):
    addon_short_name = 's3compatb3'

    REQUIRED_URLS = []

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        user_settings = self.node_settings.user_settings or self.user_settings

        result = {
            'accounts': node.api_url_for('s3compatb3_account_list'),
            'createBucket': node.api_url_for('s3compatb3_create_bucket'),
            'importAuth': node.api_url_for('s3compatb3_import_auth'),
            'create': node.api_url_for('s3compatb3_add_user_account'),
            'deauthorize': node.api_url_for('s3compatb3_deauthorize_node'),
            'folders': node.api_url_for('s3compatb3_folder_list'),
            'config': node.api_url_for('s3compatb3_set_config'),
            'files': node.web_url_for('collect_file_trees'),
            'attachedService': node.api_url_for('s3compatb3_attached_service'),
        }
        if user_settings:
            result['owner'] = web_url_for('profile_view_id',
                uid=user_settings.owner._id)
        return result

    def serialized_folder(self, node_settings):
        return {
            'path': node_settings.folder_id,
            'name': node_settings.folder_name
        }

    def credentials_are_valid(self, user_settings, client=None):
        if user_settings:
            for account in user_settings.external_accounts.all():
                if utils.can_list(account.provider_id.split('\t')[0],
                                  account.oauth_key, account.oauth_secret):
                    return True
        return False
