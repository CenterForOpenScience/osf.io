from website.addons.base.serializer import OAuthAddonSerializer
from website.util import web_url_for


class GitHubSerializer(OAuthAddonSerializer):

    @property
    def addon_serialized_urls(self):

        node = self.node_settings.owner
        user_settings = self.user_settings

        result = {
            'create_repo': node.api_url_for('github_create_repo'),
            'import_auth': node.api_url_for('github_add_user_auth'),
            'create_auth': node.api_url_for('github_oauth_start'),
            'deauthorize': node.api_url_for('github_remove_user_auth'),
            'repo_list': node.api_url_for('github_repo_list'),
            'set_repo': node.api_url_for('github_set_config'),
            'settings': web_url_for('user_addons'),
            'files': node.web_url_for('collect_file_trees'),
        }
        if user_settings:
            result['owner'] = web_url_for('profile_view_id',
                                          uid=user_settings.owner._primary_key)
        return result