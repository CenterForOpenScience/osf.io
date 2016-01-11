from website.addons.base.serializer import OAuthAddonSerializer
from webs.addons.s3 import utils

class S3Serializer(OAuthAddonSerializer):
    addon_short_name = 's3'

    REQUIRED_URLS = []

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        user_settings = self.node_settings.user_settings or self.user_settings

        result = {
            'create_bucket': node.api_url_for('create_bucket'),
            'import_auth': node.api_url_for('s3_node_import_auth'),
            'create_auth': node.api_url_for('s3_authorize_node'),
            'deauthorize': node.api_url_for('s3_delete_node_settings'),
            'bucket_list': node.api_url_for('s3_get_bucket_list'),
            'set_bucket': node.api_url_for('s3_get_node_settings'),
            'files': node.web_url_for('collect_file_trees'),
        }
        if user_settings:
            result['owner'] = user_settings.owner._id
        return result

    def credentials_are_valid(self, user_settings, client):
        if user_settings:
            if len(user_settings.external_accounts) < 1:
                return False
            return any([utils.can_list(account.oauth_key, account.oauth_secret)
                for account in user_settings.external_accounts])
        return False
