import abc

from website.util import api_url_for, web_url_for

class AddonSerializer(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, addon_node_settings, user):
        self.addon_node_settings = addon_node_settings
        self.user = user

    @abc.abstractproperty
    def serialized_urls(self):
        pass

    @abc.abstractproperty
    def has_valid_credentials(self):
        pass

    @abc.abstractproperty
    def node_has_auth(self):
        pass

    @abc.abstractproperty
    def user_has_auth(self):
        pass

    @abc.abstractproperty
    def user_is_owner(self):
        pass

    @abc.abstractproperty
    def credentials_owner(self):
        pass

    @property
    def serialized_settings(self):
        node_has_auth = self.node_has_auth
        result = {
            'nodeHasAuth': node_has_auth,
            'userHasAuth': self.user_has_auth,
            'userIsOwner': self.user_is_owner,
            'validCredentials': self.has_valid_credentials,
            'urls': self.serialized_urls,
        }

        if node_has_auth:
            owner = self.credentials_owner
            if owner:
                result['urls']['owner'] = web_url_for('profile_view_id',
                                                  uid=owner._primary_key)
                result['ownerName'] = owner.fullname
            result['folder'] = self.addon_node_settings.selected_folder_name

        return result

class StorageAddonSerializer(AddonSerializer):

    @abc.abstractproperty
    def serialized_folder(self):
        pass

    @property
    def serialized_settings(self):

        result = super(StorageAddonSerializer, self).serialized_settings
        result['folder'] = self.serialized_folder
        return result

class CitationsAddonSerializer(AddonSerializer):

    def __init__(self, addon_node_settings, user, provider_name):
        super(CitationsAddonSerializer, self).__init__(addon_node_settings, user)
        self.provider_name = provider_name

    def _serialize_account(self, external_account):
        if external_account is None:
            return None
        return {
            'id': external_account._id,
            'provider_id': external_account.provider_id,
            'display_name': external_account.display_name,
        }

    @abc.abstractproperty
    def serialized_model(self):
        pass

    @property
    def serialized_urls(self):
        external_account = self.addon_node_settings.external_account
        ret = {
            'auth': api_url_for('oauth_connect',
                                service_name=self.addon_node_settings.provider_name),
            'settings': web_url_for('user_addons'),
            'files': self.addon_node_settings.owner.url,
        }
        if external_account and external_account.profile_url:
            ret['owner'] = external_account.profile_url

        node = self.addon_node_settings.owner

        ret.update({
            'importAuth': node.api_url_for('add_user_auth'),
            'folders': node.api_url_for('citation_list'),
            'config': node.api_url_for('set_config'),
            'deauthorize': node.api_url_for('remove_user_auth'),
            'accounts': node.api_url_for('list_accounts_user'),
        })

        return ret

    @property
    def user_accounts(self):
        return [account for account in self.user.external_accounts
                if account.provider == self.provider_name]

    @property
    def has_valid_credentials(self):
        # TODO
        return True

    @property
    def node_has_auth(self):
        return self.addon_node_settings.has_auth

    @property
    def user_has_auth(self):
        user_accounts = self.user_accounts
        user_settings = self.user.get_addon(self.provider_name)
        return bool(user_settings and user_accounts)

    @property
    def user_is_owner(self):
        node_has_auth = self.node_has_auth
        user_accounts = self.user_accounts
        return (node_has_auth and (self.addon_node_settings.external_account in user_accounts)) or bool(len(user_accounts))

    @property
    def credentials_owner(self):
        return self.addon_node_settings.user_settings.owner

    def serialized_account(self):
        external_account = self.addon_node_settings.external_account
        if external_account is None:
            return None
        return {
            'id': external_account._id,
            'provider_id': external_account.provider_id,
            'display_name': external_account.display_name,
        }

    def serialize_account(self, external_account):
        if external_account is None:
            return None
        return {
            'id': external_account._id,
            'provider_id': external_account.provider_id,
            'display_name': external_account.display_name,
        }
    @abc.abstractmethod
    def serialize_folder(self, folder):
        pass

    def serialize_citation(self, citation):
        return {
            'csl': citation,
            'kind': 'file',
            'id': citation['id'],
        }
