from oauthlib.oauth2 import InvalidGrantError

from addons.base.serializer import StorageAddonSerializer
from website.util import api_url_for


class BitbucketSerializer(StorageAddonSerializer):

    addon_short_name = 'bitbucket'

    def credentials_are_valid(self, user_settings, client):
        try:
            self.node_settings.fetch_access_token()
        except (InvalidGrantError, AttributeError):
            return False
        return True

    def serialized_folder(self, node_settings):
        return {
            'path': node_settings.repo,
            'name': '{0} / {1}'.format(node_settings.user, node_settings.repo),
        }

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        return {
            'auth': api_url_for('oauth_connect', service_name='bitbucket'),
            'importAuth': node.api_url_for('bitbucket_import_auth'),
            'files': node.web_url_for('collect_file_trees'),
            'folders': node.api_url_for('bitbucket_root_folder'),
            'config': node.api_url_for('bitbucket_set_config'),
            'deauthorize': node.api_url_for('bitbucket_deauthorize_node'),
            'accounts': node.api_url_for('bitbucket_account_list'),
        }
