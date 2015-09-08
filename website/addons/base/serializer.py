import abc

from framework.auth.decorators import collect_auth
from website.util import api_url_for, web_url_for


class AddonSerializer(object):
    __metaclass__ = abc.ABCMeta

    # TODO take addon_node_settings, addon_user_settings
    def __init__(self, node_settings=None, user_settings=None):
        self.node_settings = node_settings
        self.user_settings = user_settings

    @abc.abstractproperty
    def addon_serialized_urls(self):
        pass

    @abc.abstractproperty
    def serialized_urls(self):
        pass

    @abc.abstractproperty
    def user_is_owner(self):
        pass

    @abc.abstractproperty
    def credentials_owner(self):
        pass

    @property
    def serialized_node_settings(self):
        result = {
            'nodeHasAuth': self.node_settings.has_auth,
            'userIsOwner': self.user_is_owner,
            'urls': self.serialized_urls,
        }

        if self.user_settings:
            result['userHasAuth'] = self.user_settings.has_auth
        else:
            result['userHasAuth'] = False

        if self.node_settings.has_auth:
            owner = self.credentials_owner
            if owner:
                result['urls']['owner'] = web_url_for('profile_view_id',
                                                  uid=owner._primary_key)
                result['ownerName'] = owner.fullname
        return result

    @property
    def serialized_user_settings(self):
        return {}


class OAuthAddonSerializer(AddonSerializer):

    REQUIRED_URLS = ['importAuth', 'folders', 'config', 'deauthorize', 'accounts']

    @property
    def serialized_accounts(self):
        return [
            self.serialize_account(each)
            for each in self.user_settings.external_accounts
        ]

    @property
    def serialized_user_settings(self):
        retval = super(OAuthAddonSerializer, self).serialized_user_settings
        retval['accounts'] = []
        if self.user_settings:
            retval['accounts'] = self.serialized_accounts

        return retval

    def serialize_account(self, external_account):
        if external_account is None:
            return None
        return {
            'id': external_account._id,
            'provider_id': external_account.provider_id,
            'provider_name': external_account.provider_name,
            'provider_short_name': external_account.provider,
            'display_name': external_account.display_name,
            'profile_url': external_account.profile_url,
            'nodes': [
                self.serialize_granted_node(node)
                for node in self.user_settings.get_attached_nodes(
                    external_account=external_account
                )
            ],
        }

    @collect_auth
    def serialize_granted_node(self, node, auth):

        node_settings = node.get_addon(
            self.user_settings.oauth_provider.short_name
        )
        serializer = node_settings.serializer(node_settings=node_settings)
        urls = serializer.addon_serialized_urls
        urls['view'] = node.url

        return {
            'id': node._id,
            'title': node.title if node.can_view(auth) else None,
            'urls': urls,
        }

    @property
    def serialized_urls(self):
        external_account = self.node_settings.external_account
        ret = {
            'auth': api_url_for('oauth_connect',
                                service_name=self.node_settings.provider_name),
            'settings': web_url_for('user_addons'),
        }
        if external_account and external_account.profile_url:
            ret['owner'] = external_account.profile_url

        addon_urls = self.addon_serialized_urls
        # Make sure developer returns set of needed urls
        for url in self.REQUIRED_URLS:
            msg = "addon_serialized_urls must include key '{0}'".format(url)
            assert url in addon_urls, msg
        ret.update(addon_urls)
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
    def serialized_node_settings(self):
        result = super(OAuthAddonSerializer, self).serialized_node_settings
        if self.node_settings.oauth_provider.short_name != 'dataverse':
            result['folder'] = {'name': self.node_settings.selected_folder_name}
        return result


class CitationsAddonSerializer(OAuthAddonSerializer):

    @abc.abstractmethod
    def serialize_folder(self, folder):
        pass

    def serialize_citation(self, citation):
        return {
            'csl': citation,
            'kind': 'file',
            'id': citation['id'],
        }
