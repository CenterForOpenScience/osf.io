# -*- coding: utf-8 -*-
from website.oauth.models import ExternalAccount
from website.security import encrypt, decrypt


class ExternalAccountConverter:
    """
        OwnCloudProvider from website.addons.owncloud.models hijacks the oauth
        framework to serialize account credentials for owncloud.
        ExternalAccountConverter provides a wrapper class for mapping between
        the two.
    """
    def __init__(self, account=None, host=None, username=None, password=None):
        self.account = account
        if account:
            self.host = account.oauth_key
            self.username = account.display_name
            self.password = decrypt(account.oauth_secret)
        elif not account and not host:
            self.host = None
            self.username = None
            self.password = None
        else:
            self.account = ExternalAccount(
                provider='owncloud',
                provider_name='owncloud',
                display_name=username,
                oauth_key=host,
                oauth_secret=encrypt(password),
                provider_id=host
            )

from website.addons.base.logger import AddonNodeLogger

class OwnCloudNodeLogger(AddonNodeLogger):

    addon_short_name = 'owncloud'

    def _log_params(self):
        node_settings = self.node.get_addon('owncloud')
        return {
            'project': self.node.parent_id,
            'node': self.node._primary_key,
            'folder': node_settings.folder_name if node_settings else None
        }
