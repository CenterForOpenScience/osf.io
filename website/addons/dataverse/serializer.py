from website.addons.base.serializer import OAuthAddonSerializer
from website.util import api_url_for, web_url_for


class DataverseSerializer(OAuthAddonSerializer):

    REQUIRED_URLS = []

    # Note: This information is already stored, but not serialized clearly
    def serialize_account(self, external_account):
        ret = super(DataverseSerializer, self).serialize_account(external_account)
        ret.update({
            'host': external_account.display_name,
            'host_url': 'https://{0}'.format(external_account.display_name),
        })

        return ret

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

    @property
    def serialized_urls(self):
        external_account = self.node_settings.external_account
        ret = {
            'auth': api_url_for('oauth_connect',
                                service_name=self.node_settings.provider_name),
            'settings': web_url_for('user_addons'),
            'files': self.node_settings.owner.url,
        }
        if external_account and external_account.profile_url:
            ret['owner'] = external_account.profile_url

        addon_urls = self.addon_serialized_urls
        # Make sure developer returns set of needed urls
        for url in self.REQUIRED_URLS:
            assert url in addon_urls, "addon_serilized_urls must include key '{0}'".format(url)
        ret.update(addon_urls)
        return ret

    @property
    def addon_serialized_urls(self):
        # node = self.node_settings.owner
        #
        # return {
        #     'importAuth': node.api_url_for('dataverse_add_user_auth'),
        #     'config': node.api_url_for('dataverse_set_config'),
        #     'deauthorize': node.api_url_for('dataverse_remove_user_auth'),
        #     'accounts': node.api_url_for('dataverse_get_user_accounts'),
        # }

        return {}
