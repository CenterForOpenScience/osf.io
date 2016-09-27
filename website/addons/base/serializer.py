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
    def addon_short_name(self):
        pass

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

    @property
    def credentials_owner(self):
        return self.user_settings.owner if self.user_settings else None

    @property
    def user_is_owner(self):
        if self.user_settings is None or self.node_settings is None:
            return False

        user_accounts = self.user_settings.external_accounts
        return bool(
            self.node_settings.has_auth and
            self.node_settings.external_account in user_accounts
        )

    @property
    def serialized_urls(self):
        ret = self.addon_serialized_urls
        # Make sure developer returns set of needed urls
        for url in self.REQUIRED_URLS:
            msg = "addon_serialized_urls must include key '{0}'".format(url)
            assert url in ret, msg
        ret.update({'settings': web_url_for('user_addons')})
        return ret

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


class StorageAddonSerializer(OAuthAddonSerializer):

    REQUIRED_URLS = ('auth', 'importAuth', 'folders', 'files', 'config', 'deauthorize', 'accounts')

    @abc.abstractmethod
    def credentials_are_valid(self, user_settings):
        pass

    @abc.abstractmethod
    def serialized_folder(self, node_settings):
        pass

    def serialize_settings(self, node_settings, current_user, client=None):
        user_settings = node_settings.user_settings
        self.node_settings = node_settings
        current_user_settings = current_user.get_addon(self.addon_short_name)
        user_is_owner = user_settings is not None and user_settings.owner == current_user

        valid_credentials = self.credentials_are_valid(user_settings, client)

        result = {
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
            # Show available folders
            if node_settings.folder_id is None:
                result['folder'] = {'name': None, 'path': None}
            elif valid_credentials:
                result['folder'] = self.serialized_folder(node_settings)
        return result


class CitationsAddonSerializer(OAuthAddonSerializer):

    REQUIRED_URLS = ('importAuth', 'folders', 'config', 'deauthorize', 'accounts')

    serialized_root_folder = {
        'name': 'All Documents',
        'provider_list_id': None,
        'id': 'ROOT',
        'parent_list_id': '__',
        'kind': 'folder',
    }

    @property
    def serialized_urls(self):
        external_account = self.node_settings.external_account
        ret = {
            'auth': api_url_for('oauth_connect',
                                service_name=self.addon_short_name),
            'files': self.node_settings.owner.url,
        }
        if external_account and external_account.profile_url:
            ret['owner'] = external_account.profile_url

        ret.update(super(CitationsAddonSerializer, self).serialized_urls)
        return ret

    @property
    def serialized_node_settings(self):
        result = super(CitationsAddonSerializer, self).serialized_node_settings
        result['folder'] = {
            'name': self.node_settings.fetch_folder_name
        }
        return result

    @property
    def credentials_owner(self):
        return self.node_settings.user_settings.owner

    def serialize_folder(self, folder):
        return {
            'data': folder,
            'kind': 'folder',
            'name': folder['name'],
            'id': folder['id'],
            'urls': {
                'fetch': self.node_settings.owner.api_url_for(
                    '{0}_citation_list'.format(self.addon_short_name),
                    list_id=folder['id']
                ),
            },
        }

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        return {
            'importAuth': node.api_url_for('{0}_import_auth'.format(self.addon_short_name)),
            'folders': node.api_url_for('{0}_citation_list'.format(self.addon_short_name)),
            'config': node.api_url_for('{0}_set_config'.format(self.addon_short_name)),
            'deauthorize': node.api_url_for('{0}_deauthorize_node'.format(self.addon_short_name)),
            'accounts': node.api_url_for('{0}_account_list'.format(self.addon_short_name)),
        }

    def serialize_citation(self, citation):
        return {
            'csl': citation,
            'kind': 'file',
            'id': citation['id'],
        }
