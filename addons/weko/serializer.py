from addons.base.serializer import OAuthAddonSerializer
from . import settings as weko_settings
from .apps import SHORT_NAME
from website.util import api_url_for, web_url_for

from admin.rdm_addons.utils import get_rdm_addon_option

from requests import exceptions as requests_exceptions


def get_repository_options(user):
    repos = list(weko_settings.REPOSITORY_IDS)
    for institution_id in user.affiliated_institutions.all():
        rdm_addon_option = get_rdm_addon_option(institution_id, SHORT_NAME, create=False)
        if rdm_addon_option is None:
            continue
        for account in rdm_addon_option.external_accounts.all():
            display_name = account.display_name if '#' not in account.display_name else account.display_name[account.display_name.index('#') + 1:]
            repos.append({
                'id': account.provider_id,
                'name': display_name,
            })
    return repos


class WEKOSerializer(OAuthAddonSerializer):

    addon_short_name = 'weko'

    REQUIRED_URLS = []

    def credentials_are_valid(self, user_settings, cl):
        try:
            c = self.node_settings.create_client()
            if c is None:
                return False
            c.get_login_user()
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

        # Update with WEKO specific fields
        if self.node_settings.has_auth:
            c = self.node_settings.create_client()
            indices = c.get_indices()

            result.update({
                'validCredentials': True,
                'indices': [self._serialize_index(index) for index in indices],
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
            'repositories': get_repository_options(current_user),
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

    def _serialize_index(self, index):
        return {
            'title': index.title,
            'id': index.identifier,
            'children': [self._serialize_index(i) for i in index.children],
        }
