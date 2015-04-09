from website.addons.base.serializer import GenericAddonSerializer
from website.util import web_url_for


class GitHubSerializer(GenericAddonSerializer):

    @property
    def addon_serialized_urls(self):

        node = self.node_settings.owner
        user_settings = self.user_settings

        result = {
            'create_repo': node.api_url_for('github_create_repo'),
            'importAuth': node.api_url_for('github_add_user_auth'),
            # 'create_auth': node.api_url_for('github_oauth_start'),
            'deauthorize': node.api_url_for('github_remove_user_auth'),
            'repos': node.api_url_for('github_repo_list'),
            'config': node.api_url_for('github_set_config'),
            'settings': web_url_for('user_addons'),
            'accounts': node.api_url_for('github_get_user_accounts'),
            'files': node.web_url_for('collect_file_trees'),
        }
        if user_settings:
            result['owner'] = web_url_for('profile_view_id',
                                          uid=user_settings.owner._primary_key)
        return result

    @property
    def serialized_node_settings(self):
        result = super(GitHubSerializer, self).serialized_node_settings
        result['repo'] = {'name': self.node_settings.repo}
        valid_credentials = True
        if self.node_settings.external_account is not None:
            self.node_settings.fetch_access_token()
        result['validCredentials'] = valid_credentials
        return {'result': result}
