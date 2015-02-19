import abc

from website.oauth.models import ExternalAccount

from website.util import api_url_for, web_url_for
from . import utils

class CitationsProvider(object):

    __metaclass__ = abc.ABCMeta
    
    def __init__(self, provider_name):
        
        self.provider_name = provider_name
        
    @abc.abstractmethod
    def _serialize_urls(self, node_addon):
        """ Collects and serializes urls needed for AJAX calls """

        external_account = node_addon.external_account
        node = node_addon.owner                
        ret = {
            'auth': api_url_for('oauth_connect',
                                service_name=self.provider_name),
            'settings': web_url_for('user_addons'),
        }
        if external_account and external_account.profile_url:
            ret['owner'] = external_account.profile_url
            
        return ret    


    @abc.abstractmethod
    def _serialize_model(self, node_addon, user):
        
        return {}
        
        
    def serialize_settings(self, node_settings, current_user):
        """ Collects and serializes parameters for building UI for widget and settings pages """
        node_account = node_settings.external_account
        user_accounts = [account for account in current_user.external_accounts
                         if account.provider == 'mendeley']

        user_is_owner = node_account and node_account in user_accounts

        user_settings = current_user.get_addon('mendeley')
        user_has_auth = bool(user_settings and user_accounts)

        user_account_id = None
        if user_has_auth:
            user_account_id = user_accounts[0]._id

        result = {
            'nodeHasAuth': node_settings.has_auth,
            'userIsOwner': user_is_owner,
            'userHasAuth': user_has_auth,
            'urls': self._serialize_urls(node_settings),
            'userAccountId': user_account_id,
        }
        if node_account is not None:
            result['folder'] = node_settings.selected_folder_name
            result['ownerName'] = node_account.display_name

        result.update(self._serialize_model(node_settings, current_user))        
        return result

        
    def user_accounts(self, user):
        """ Gets a list of the accounts authorized by 'user' """
        return {
            'accounts': [
                utils.serialize_account(each)
                for each in user.external_accounts
                if each.provider == self.provider_name
            ]
        }


    def set_config(self, node_addon, user, external_account_id, external_list_id):
        # Ensure request has all required information
        try:
            external_account = ExternalAccount.load(external_account_id)
        except KeyError:
            raise HTTPError(http.BAD_REQUEST)
            
        # User is an owner of this ExternalAccount
        if external_account in user.external_accounts:
            # grant access to the node for the Mendeley list
            node_addon.grant_oauth_access(
                user=user,
                external_account=external_account,
                metadata={'lists': external_list_id},
            )            
        else: # User doesn't own the ExternalAccount
            # Make sure the node has previously been granted access
            if not node_addon.verify_oauth_access(external_account, list_id):
                raise HTTPError(http.FORBIDDEN)
        return external_account
                
    def add_user_auth(self, node_addon, user, external_account_id):
        
        external_account = ExternalAccount.load(external_account_id)        
        if external_account not in user.external_accounts:
            raise HTTPError(http.FORBIDDEN)

        user_addon = user.get_or_add_addon(self.provider_name)

        node_addon.grant_oauth_access(user_addon.owner, external_account)
        node_addon.external_account = external_account
        node_addon.save()
        result = self.serialize_settings(node_addon, user)
        return {'result': result}

        
    @abc.abstractmethod
    def remove_user_auth(self, node_addon, user):

        node_addon.external_account = None
        node_addon.save() 
        result = self.serialize_settings(node_addon, user)
        return {'result': result}

        
    def widget(self, node_addon):
        
        ret = node_addon.config.to_json()
        ret.update({
            'complete': node_addon.complete,
        })
        return ret

    @abc.abstractmethod
    def citation_list(self, node_addon, user, list_id, show='all'):

        return {}
    
