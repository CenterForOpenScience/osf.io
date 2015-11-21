# -*- coding: utf-8 -*-
import logging
import requests

from flask import abort, request

import onedrivesdk
from onedrivesdk.helpers import GetAuthCodeServer

#from onedrivesdk import CredentialsV2, OnedriveClient
#from onedrivesdk.client import OnedriveClientException
from modularodm import fields

from framework.auth import Auth
from framework.exceptions import HTTPError

from website.addons.base import exceptions
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase

from website.addons.onedrive import settings
from website.addons.onedrive.utils import OnedriveNodeLogger
from website.addons.onedrive.serializer import OnedriveSerializer
from website.oauth.models import ExternalProvider

logger = logging.getLogger(__name__)

logging.getLogger('onedrive1').setLevel(logging.WARNING)

class Onedrive(ExternalProvider):
    name = 'Onedrive'
    short_name = 'onedrive'

    client_id = settings.ONEDRIVE_KEY
    client_secret = settings.ONEDRIVE_SECRET

    auth_url_base = settings.ONEDRIVE_OAUTH_AUTH_ENDPOINT
    callback_url = settings.ONEDRIVE_OAUTH_TOKEN_ENDPOINT
    auto_refresh_url = settings.ONEDRIVE_OAUTH_TOKEN_ENDPOINT
    default_scopes = ['wl.basic wl.signin onedrive.readwrite wl.offline_access']

    

    def handle_callback(self, response):        
        """View called when the Oauth flow is completed. Adds a new OnedriveUserSettings
        record to the user and saves the user's access token and account info.
        """

        logger.error('Onedrive::handle_callback')
        logger.error('Onedrive::response' + repr(response))
        code = request.args.get('code')
        uid = str(response['user_id'])
        
        r = requests.get('https://apis.live.net/v5.0/b3b92fbe54bee8b6?access_token='+response['access_token'])
        logger.error('https://apis.live.net/v5.0/'+uid+'?access_token=EwCIAq1DBAAUGCCXc8wU/zFu9QnLdZXy+YnElFkAAWG1tIiEesh52LlMfTJYF8ZS3v5wYnQ8Gy+y6cmRu19JAC7tOKAw0pv58/wM8rsZlFSby28ahai2xrHwhWa78JfMQ7UvnKQwnK4UEYSX/3Cz/qJniHHMnBP56Z9xG+Ek2+G2udjfUm/5NNtpLgA62msHuWwVSfDgWXgAzAkgXRrGHtxwW6VeryQfLLN++wBzV6SJ34tbumB7Fu3IzCEMxkh642Ww+JvsZhKbj9I8xH4HC83y8b2pJ6Erh5afmmRl5JbtiIY94tBAHRIGsHQRnVjJoQpZVivDFh+EaGw9w6za00zRrAqqx5DAPGT4PaeluhLGF3CVi8ZxaNQjOUKwDCoDZgAACOfvLIBOAAO5WAEtTon0n4NeTw4slGh0sNQFD067s311bInKEuIm/id1ZBoMXqUvbin2lKVZy+CKPORBqiXDMnzK0DM1IyfQcp4cliM3VLoDlAaU6AfDNM1qRskmQhL/S6p600bsFyF15XLc23QdYKFzSY/nFtRAyKY7mUmE82DijwaQZSmBmH8l07xN+kza06MLI72gmTiGDiTeqTMVSaNmrn5/mpnAIeGFflqxUNJ+S9wMpeA58u+L3xH2BydoKxJFrCFwSzk+UleBlm4Yim5Tl+w6WbKPpb9oALxM0nhiYV7GMUx0wAXJAf9Z07dLUPyHu/fCU/8abccf21k1/oZEXiHA+uHaAsH+fRvHJ6Q+UUVkTLllgRMBDUY2ZzhOdqWKEGqnAef/cPX3epZaG94jtgkt9A9EQvhgbb5zgWX2DA1ozzuOsHclXLdfk6KBSsTKLwKXpc/8zH2QZXgLTf0f1XQB')
        
        logger.error('Onedrive::full url' + repr(r))
        logger.error('Onedrive::json' + repr(r.json()))
        #grabbed the JSON from the profile
        #raise ValueError('lets stop here, code:' + code)
#         client = OnedriveClient(CredentialsV2(
#             response['access_token'],
#             response['refresh_token'],
#             settings.ONEDRIVE_KEY,
#             settings.ONEDRIVE_SECRET,
#         ))
# 
#         about = client.get_user_info()

        return {
            'user_id': r.json()['id'],
            'provider_id': response['user_id'],
            'code': code,
            'display_name': r.json()['name'],
            'profile_url': r.json()['link']
        }

class OnedriveUserSettings(AddonOAuthUserSettingsBase):
    """Stores user-specific onedrive information
    """
    oauth_provider = Onedrive
    serializer = OnedriveSerializer
    myBase = AddonOAuthUserSettingsBase


class OnedriveNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):

    oauth_provider = Onedrive
    serializer = OnedriveSerializer

    foreign_user_settings = fields.ForeignField(
        'onedriveusersettings', backref='authorized'
    )
    folder_id = fields.StringField(default=None)
    folder_name = fields.StringField()
    folder_path = fields.StringField()

    _folder_data = None

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = Onedrive(self.external_account)
        return self._api

    @property
    def display_name(self):
        return '{0}: {1}'.format(self.config.full_name, self.folder_id)

    @property
    def has_auth(self):
        """Whether an access token is associated with this node."""
        return bool(self.user_settings and self.user_settings.has_auth)

    @property
    def complete(self):
        return bool(self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
        ))

    def fetch_folder_name(self):
        self._update_folder_data()
        return self.folder_name.replace('All Files', '/ (Full Onedrive)')

    def fetch_full_folder_path(self):
        self._update_folder_data()
        return self.folder_path

    def _update_folder_data(self):
        if self.folder_id is None:
            return None

        if not self._folder_data:

            self.folder_name = self._folder_data['name']
            self.folder_path = '/'.join(
                [x['name'] for x in self._folder_data['path_collection']['entries']]
                + [self._folder_data['name']]
            )
            self.save()

    def set_folder(self, folder_id, auth):
        self.folder_id = str(folder_id)
        self._update_folder_data()
        self.save()

        if not self.complete:
            self.user_settings.grant_oauth_access(
                node=self.owner,
                external_account=self.external_account,
                metadata={'folder': self.folder_id}
            )
            self.user_settings.save()

        # Add log to node
        nodelogger = OnedriveNodeLogger(node=self.owner, auth=auth)
        nodelogger.log(action="folder_selected", save=True)

    def set_user_auth(self, user_settings):
        """Import a user's Onedrive authentication and create a NodeLog.

        :param OnedriveUserSettings user_settings: The user settings to link.
        """
        self.user_settings = user_settings
        nodelogger = OnedriveNodeLogger(node=self.owner, auth=Auth(user_settings.owner))
        nodelogger.log(action="node_authorized", save=True)

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        node = self.owner

        if add_log:
            extra = {'folder_id': self.folder_id}
            nodelogger = OnedriveNodeLogger(node=node, auth=auth)
            nodelogger.log(action="node_deauthorized", extra=extra, save=True)

        self.folder_id = None
        self._update_folder_data()
        self.user_settings = None
        self.clear_auth()

        self.save()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')

    def serialize_waterbutler_settings(self):
        if self.folder_id is None:
            raise exceptions.AddonError('Folder is not configured')
        return {'folder': self.folder_id}

    def create_waterbutler_log(self, auth, action, metadata):
        self.owner.add_log(
            'onedrive_{0}'.format(action),
            auth=auth,
            params={
                'path': metadata['materialized'],
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'folder': self.folder_id,
                'urls': {
                    'view': self.owner.web_url_for('addon_view_or_download_file', provider='onedrive', action='view', path=metadata['path']),
                    'download': self.owner.web_url_for('addon_view_or_download_file', provider='onedrive', action='download', path=metadata['path']),
                },
            },
        )

    ##### Callback overrides #####
    def after_delete(self, node=None, user=None):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.clear_auth()
        self.save()
