from website.addons.base.serializer import OAuthAddonSerializer
from website.util import api_url_for, web_url_for


class GitHubSerializer(OAuthAddonSerializer):

    @property
    def serialized_urls(self):
        if self.node_settings is None:
            return ''

        external_account = self.node_settings.external_account
        ret = {
            'auth': api_url_for('oauth_connect',
                                service_name=self.node_settings.provider_name),
            'settings': web_url_for('user_addons'),
        }
        if external_account and external_account.profile_url:
            ret['owner'] = external_account.profile_url

        addon_urls = self.addon_serialized_urls
        ret.update(addon_urls)
        return ret

    @property
    def addon_serialized_urls(self):
        if self.node_settings is None:
            return ''

        node = self.node_settings.owner
        user_settings = self.user_settings

        result = {
            'create_repo': node.api_url_for('github_create_repo'),
            'importAuth': node.api_url_for('github_add_user_auth'),
            'deauthorize': node.api_url_for('github_remove_user_auth'),
            'repo_list': node.api_url_for('github_repo_list'),
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
        result['repo'] = self.node_settings.repo
        result['user'] = self.node_settings.user
        return {'result': result}

    @property
    def user_is_owner(self):
        if self.user_settings is None:
            return False
        user_accounts = self.user_settings.external_accounts
        return bool(
            (
                self.node_settings.has_auth and
                (self.node_settings.external_account in user_accounts)
            ) or len(user_accounts)
        )

    @property
    def credentials_owner(self):
        return self.node_settings.user_settings.owner
