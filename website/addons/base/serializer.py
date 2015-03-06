import abc

from website.util import api_url_for, web_url_for

class AddonSerializer(object):
    __metaclass__ = abc.ABCMeta

    # TODO take addon_node_settings, addon_user_settings
    def __init__(self, addon_node_settings, user):
        self.addon_node_settings = addon_node_settings
        self.user = user

    @abc.abstractproperty
    def addon_serialized_urls(self):
        pass

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

    REQUIRED_URLS = ['importAuth', 'folders', 'config', 'deauthorize', 'accounts']

    def __init__(self, addon_node_settings, user, provider_name):
        super(CitationsAddonSerializer, self).__init__(addon_node_settings, user)
        self.provider_name = provider_name

    '''
    def _serialize_account(self, external_account):
        if external_account is None:
            return None
        return {
            'id': external_account._id,
            'provider_id': external_account.provider_id,
            'display_name': external_account.display_name,
        }
    '''

    '''
    @abc.abstractproperty
    def serialized_model(self):
        pass
    '''

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

        addon_urls = self.addon_serialized_urls
        # Make sure developer returns set of needed urls
        for url in self.REQUIRED_URLS:
            assert url in addon_urls, "addon_serilized_urls must include key '{0}'".format(url)
        ret.update(addon_urls)
        return ret

    @property
    def serialized_settings(self):
        result = super(CitationsAddonSerializer, self).serialized_settings
        result['folder'] = self.addon_node_settings.selected_folder_name
        return result

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
