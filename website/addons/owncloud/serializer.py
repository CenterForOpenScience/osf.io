from website.addons.base.serializer import OAuthAddonSerializer
from website.addons.owncloud.settings import DEFAULT_HOSTS
from website.util import api_url_for, web_url_for
from website.addons.owncloud.utils import ExternalAccountConverter

class OwnCloudSerializer(OAuthAddonSerializer):

    addon_short_name = 'owncloud'

    REQUIRED_URLS = []

    # Include host information with more informative labels / formatting
    def serialize_account(self, external_account):
        ret = super(OwnCloudSerializer, self).serialize_account(external_account)
        converted = ExternalAccountConverter(external_account)
        ret.update({
            'host': converted.host,
            'host_url': 'https://{0}'.format(converted.host),
        })

        return ret

    def serialized_folder(self, node_settings):
        return {
            'name': node_settings.folder_name,
            'path': node_settings.folder_name
        }

    @property
    def credentials_owner(self):
        return self.node_settings.user_settings.owner

    @property
    def serialized_urls(self):
        external_account = self.node_settings.external_account
        node = self.node_settings.owner
        ret = {
            'settings': web_url_for('user_addons'),
            'folders': node.api_url_for('owncloud_folder_list'),
            'files': node.api_url_for('owncloud_folder_list'),
            'config': node.api_url_for('owncloud_set_config'),
        }
        # Dataverse users do not currently have profile URLs
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
        node = self.node_settings.owner

        return {
            'create': api_url_for('owncloud_add_user_account'),
            'set': node.api_url_for('owncloud_set_config'),
            'importAuth': node.api_url_for('owncloud_import_auth'),
            'deauthorize': node.api_url_for('owncloud_deauthorize_node'),
            'accounts': api_url_for('owncloud_account_list'),
        }

    @property
    def serialized_node_settings(self):
        result = super(OwnCloudSerializer, self).serialized_node_settings
        result['hosts'] = DEFAULT_HOSTS

        # Update with Dataverse specific fields
        if self.node_settings.has_auth:
            result.update({'folder': self.node_settings.folder_name})
        return result

    def serialize_settings(self, node_settings, user):
        if not self.node_settings:
            self.node_settings = node_settings
        if not self.user_settings:
            self.user_settings = user.get_addon(self.addon_short_name)
        return self.serialized_node_settings
