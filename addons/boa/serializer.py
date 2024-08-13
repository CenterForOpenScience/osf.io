from boaapi.boa_client import BoaClient, BOA_API_ENDPOINT, BoaException

from addons.base.exceptions import NotApplicableError
from addons.base.serializer import StorageAddonSerializer
from addons.boa.settings import DEFAULT_HOSTS
from framework import sentry
from website.util import web_url_for


class BoaSerializer(StorageAddonSerializer):

    addon_short_name = 'boa'

    def serialized_folder(self, node_settings):
        """Not applicable to remote computing add-ons"""
        raise NotApplicableError

    def credentials_are_valid(self, user_settings, client=None):
        if client is not None:
            sentry.log_message('Client ignored for Boa Serializer in credentials_are_valid()')
        external_account = self.node_settings.external_account
        if external_account is None:
            return False
        provider = self.node_settings.oauth_provider(external_account)

        try:
            boa_client = BoaClient(endpoint=BOA_API_ENDPOINT)
            boa_client.login(provider.username, provider.password)
            boa_client.close()
            return True
        except BoaException:
            return False

    @property
    def addon_serialized_urls(self):

        node = self.node_settings.owner
        user_settings = self.node_settings.user_settings or self.user_settings

        result = {
            'auth': node.api_url_for('boa_add_user_account'),
            'accounts': node.api_url_for('boa_account_list'),
            'importAuth': node.api_url_for('boa_import_auth'),
            'deauthorize': node.api_url_for('boa_deauthorize_node'),
            'folders': None,
            'files': None,
            'config': None,
        }
        if user_settings:
            result['owner'] = web_url_for('profile_view_id', uid=user_settings.owner._id)
        return result

    @property
    def serialized_node_settings(self):
        result = super().serialized_node_settings
        result['hosts'] = DEFAULT_HOSTS
        return result

    @property
    def serialized_user_settings(self):
        result = super().serialized_user_settings
        result['hosts'] = DEFAULT_HOSTS
        return result

    def serialize_settings(self, node_settings, current_user, client=None):
        if client is not None:
            sentry.log_message('Client ignored for Boa Serializer in serialize_settings()')
        ret = super().serialize_settings(node_settings, current_user, client=client)
        ret['hosts'] = DEFAULT_HOSTS
        return ret
