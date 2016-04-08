from website.util import web_url_for
from website.addons.base.serializer import OAuthAddonSerializer
from website.addons.s3 import utils

class S3Serializer(OAuthAddonSerializer):
    addon_short_name = 's3'

    REQUIRED_URLS = []

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        user_settings = self.node_settings.user_settings or self.user_settings

        result = {
            'accounts': node.api_url_for('s3_account_list'),
            'create_bucket': node.api_url_for('create_bucket'),
            'import_auth': node.api_url_for('s3_import_auth'),
            'create': node.api_url_for('s3_add_user_account'),
            'deauthorize': node.api_url_for('s3_deauthorize_node'),
            'bucket_list': node.api_url_for('s3_folder_list'),
            'set_bucket': node.api_url_for('s3_set_config'),
            'files': node.web_url_for('collect_file_trees'),
        }
        if user_settings:
            result['owner'] = web_url_for('profile_view_id',
                uid=user_settings.owner._id)
        return result

    def credentials_are_valid(self, user_settings):
        if user_settings:
            for account in user_settings.external_accounts:
                if utils.can_list(account.oauth_key, account.oauth_secret):
                    return True
        return False

    def serialize_settings(self, node_settings, current_user, client=None):
        self.user_settings = node_settings.user_settings
        self.node_settings = node_settings

        ret = self.node_settings.to_json(current_user)
        current_user_settings = current_user.get_addon('s3')

        ret.update({
            'bucket': self.node_settings.bucket or '',
            'encryptUploads': self.node_settings.encrypt_uploads,
            'hasBucket': self.node_settings.bucket is not None,
            'userIsOwner': (
                self.user_settings and self.user_settings.owner == current_user
            ),
            'userHasAuth': bool(current_user_settings) and current_user_settings.has_auth,
            'nodeHasAuth': self.node_settings.has_auth,
            'ownerName': None,
            'bucketList': None,
            'validCredentials': bool(current_user_settings) and self.credentials_are_valid(current_user_settings),
        })

        if self.node_settings.has_auth:
            ret['ownerName'] = self.user_settings.owner.fullname

        ret['urls'] = self.serialized_urls

        return ret
