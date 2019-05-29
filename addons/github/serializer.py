from addons.base.serializer import StorageAddonSerializer

from website.util import api_url_for

from addons.github.api import GitHubClient


class GitHubSerializer(StorageAddonSerializer):

    addon_short_name = 'github'

    def credentials_are_valid(self, user_settings, client):
        if user_settings:
            return GitHubClient(external_account=user_settings.external_accounts[0]).check_authorization()

    def serialized_folder(self, node_settings):
        return {
            'path': node_settings.repo,
            'name': '{0} / {1}'.format(node_settings.user, node_settings.repo),
        }

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner

        return {
            'auth': api_url_for('oauth_connect',
                                service_name='github'),
            'importAuth': node.api_url_for('github_import_auth'),
            'files': node.web_url_for('collect_file_trees'),
            'folders': node.api_url_for('github_folder_list'),
            'config': node.api_url_for('github_set_config'),
            'deauthorize': node.api_url_for('github_deauthorize_node'),
            'accounts': node.api_url_for('github_account_list'),
        }
