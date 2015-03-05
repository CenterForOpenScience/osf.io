import abc

from website.util import web_url_for

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

        return result

class StorageAddonSerializer(AddonSerializer):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def serialized_folder(self):
        pass

    @property
    def serialized_settings(self):

        result = super(StorageAddonSerializer, self).serialized_settings
        result['folder'] = self.serialized_folder
        return result

class CitationsAddonSerializer(AddonSerializer):
    __metaclass__ = abc.ABCMeta
