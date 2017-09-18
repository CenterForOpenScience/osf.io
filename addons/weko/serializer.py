from addons.base.serializer import OAuthAddonSerializer
from addons.weko import client
from addons.weko import settings as weko_settings
from website.util import api_url_for, web_url_for

from requests import exceptions as requests_exceptions


class WEKOSerializer(OAuthAddonSerializer):

    addon_short_name = 'weko'

    REQUIRED_URLS = []

    def credentials_are_valid(self, user_settings, cl):
        try:
            conn = client.connect_from_settings(weko_settings, self.node_settings)
            if conn is None:
                return False
            conn.get_login_user()
        except requests_exceptions.HTTPError:
            return False
        return True

    # Include host information with more informative labels / formatting
    def serialize_account(self, external_account):
        ret = super(WEKOSerializer, self).serialize_account(external_account)
        host = external_account.oauth_key
        ret.update({
            'host': host
        })

        return ret

    @property
    def credentials_owner(self):
        return self.node_settings.user_settings.owner

    @property
    def serialized_urls(self):
        external_account = self.node_settings.external_account
        ret = {
            'settings': web_url_for('user_addons'),  # TODO: Is this needed?
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
        node = self.node_settings.owner
        external_account = self.node_settings.external_account
        host = external_account.oauth_key if external_account else ''

        return {
            'auth': api_url_for('weko_oauth_connect',
                                repoid='<repoid>'),
            'set': node.api_url_for('weko_set_config'),
            'importAuth': node.api_url_for('weko_import_auth'),
            'deauthorize': node.api_url_for('weko_deauthorize_node'),
            'accounts': api_url_for('weko_account_list'),
        }

    @property
    def serialized_node_settings(self):
        result = super(WEKOSerializer, self).serialized_node_settings
        result['repositories'] = weko_settings.REPOSITORY_IDS

        # Update with WEKO specific fields
        if self.node_settings.has_auth:
            connection = client.connect_from_settings(weko_settings, self.node_settings)
            all_indices = client.get_all_indices(connection)
            indices = list(filter(lambda i: i.nested == 0, all_indices))

            result.update({
                'validCredentials': True,
                'indices': [
                    {'title': index.title, 'id': index.identifier, 'about': index.about}
                    for index in indices
                ],
                'savedIndex': {
                    'title': self.node_settings.index_title,
                    'id': self.node_settings.index_id,
                }
            })

        return result

    def serialized_folder(self, node_settings):
        return {
            'id': node_settings.index_id,
            'title': node_settings.index_title
        }

    def serialize_settings(self, node_settings, current_user, client=None):
        self.user_settings = user_settings = node_settings.user_settings
        self.node_settings = node_settings
        current_user_settings = current_user.get_addon(self.addon_short_name)
        user_is_owner = user_settings is not None and user_settings.owner == current_user

        valid_credentials = self.credentials_are_valid(user_settings, client)

        result = {
            'repositories': weko_settings.REPOSITORY_IDS,
            'userIsOwner': user_is_owner,
            'nodeHasAuth': node_settings.has_auth,
            'urls': self.serialized_urls,
            'validCredentials': valid_credentials,
            'userHasAuth': current_user_settings is not None and current_user_settings.has_auth,
        }

        if node_settings.has_auth:
            # Add owner's profile URL
            result['urls']['owner'] = web_url_for(
                'profile_view_id',
                uid=user_settings.owner._id
            )
            result['ownerName'] = user_settings.owner.fullname
            # Show available indices
            result.update(self.serialized_node_settings)
        return result
