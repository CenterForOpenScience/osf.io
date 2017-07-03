from website.addons.base.serializer import StorageAddonSerializer

from website.util import api_url_for

from website.addons.gitlab.api import GitLabClient
from website.addons.gitlab.exceptions import GitLabError

class GitLabSerializer(StorageAddonSerializer):

    addon_short_name = 'gitlab'

    # Include host information with more informative labels / formatting
    def serialize_account(self, external_account):
        ret = super(GitLabSerializer, self).serialize_account(external_account)
        host = external_account.display_name
        ret.update({
            'host': host,
            'host_url': 'https://{0}'.format(host),
        })

        return ret

    def credentials_are_valid(self, user_settings, client):
        if user_settings:
            client = client or GitLabClient(external_account=user_settings.external_accounts[0])
            try:
                client.user()
            except (GitLabError, IndexError):
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
            'auth': api_url_for('oauth_connect', service_name='GitLab'),
            'importAuth': node.api_url_for('gitlab_import_auth'),
            'files': node.web_url_for('collect_file_trees'),
            'folders': node.api_url_for('gitlab_root_folder'),
            'config': node.api_url_for('gitlab_set_config'),
            'deauthorize': node.api_url_for('gitlab_deauthorize_node'),
            'accounts': node.api_url_for('gitlab_account_list'),
        }
