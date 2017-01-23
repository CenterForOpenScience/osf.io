# -*- coding: utf-8 -*-
import httplib as http
import logging
import os

from dropbox.client import DropboxOAuth2Flow, DropboxClient
from dropbox.rest import ErrorResponse
from flask import request
from urllib3.exceptions import MaxRetryError

from modularodm import fields

from framework.auth import Auth
from framework.exceptions import HTTPError
from framework.sessions import session

from website.util import web_url_for, api_v2_url
from website.addons.base import exceptions
from website.addons.base import StorageAddonBase
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.oauth.models import ExternalProvider

from website.addons.dropbox import settings
from website.addons.dropbox.serializer import DropboxSerializer

logger = logging.getLogger(__name__)


class DropboxProvider(ExternalProvider):

    name = 'Dropbox'
    short_name = 'dropbox'

    client_id = settings.DROPBOX_KEY
    client_secret = settings.DROPBOX_SECRET

    # Explicitly override auth_url_base as None -- DropboxOAuth2Flow handles this for us
    auth_url_base = None
    callback_url = None
    handle_callback = None

    @property
    def oauth_flow(self):
        if 'oauth_states' not in session.data:
            session.data['oauth_states'] = {}
        if self.short_name not in session.data['oauth_states']:
            session.data['oauth_states'][self.short_name] = {
                'state': None
            }
        return DropboxOAuth2Flow(
            self.client_id,
            self.client_secret,
            redirect_uri=web_url_for(
                'oauth_callback',
                service_name=self.short_name,
                _absolute=True
            ),
            session=session.data['oauth_states'][self.short_name], csrf_token_session_key='state'
        )

    @property
    def auth_url(self):
        return self.oauth_flow.start('force_reapprove=true')

    # Overrides ExternalProvider
    def auth_callback(self, user):
        # TODO: consider not using client library during auth flow
        try:
            access_token, dropbox_user_id, url_state = self.oauth_flow.finish(request.values)
        except (DropboxOAuth2Flow.NotApprovedException, DropboxOAuth2Flow.BadStateException):
            # 1) user cancelled and client library raised exc., or
            # 2) the state was manipulated, possibly due to time.
            # Either way, return and display info about how to properly connect.
            return
        except (DropboxOAuth2Flow.ProviderException, DropboxOAuth2Flow.CsrfException):
            raise HTTPError(http.FORBIDDEN)
        except DropboxOAuth2Flow.BadRequestException:
            raise HTTPError(http.BAD_REQUEST)

        self.client = DropboxClient(access_token)

        info = self.client.account_info()
        return self._set_external_account(
            user,
            {
                'key': access_token,
                'provider_id': info['uid'],
                'display_name': info['display_name'],
            }
        )


class DropboxUserSettings(AddonOAuthUserSettingsBase):
    """Stores user-specific dropbox information.
    token.
    """

    oauth_provider = DropboxProvider
    serializer = DropboxSerializer

    def revoke_remote_oauth_access(self, external_account):
        """Overrides default behavior during external_account deactivation.

        Tells DropBox to remove the grant for the OSF associated with this account.
        """
        client = DropboxClient(external_account.oauth_key)
        try:
            client.disable_access_token()
        except ErrorResponse:
            pass

class DropboxNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):

    oauth_provider = DropboxProvider
    serializer = DropboxSerializer

    folder = fields.StringField(default=None)

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = DropboxProvider(self.external_account)
        return self._api

    @property
    def folder_id(self):
        return self.folder

    @property
    def folder_name(self):
        return os.path.split(self.folder or '')[1] or '/ (Full Dropbox)' if self.folder else None

    @property
    def folder_path(self):
        return self.folder

    @property
    def display_name(self):
        return '{0}: {1}'.format(self.config.full_name, self.folder)

    def clear_settings(self):
        self.folder = None

    def fetch_folder_name(self):
        return self.folder_name

    def get_folders(self, **kwargs):
        folder_id = kwargs.get('folder_id')
        if folder_id is None:
            return [{
                'addon': 'dropbox',
                'id': '/',
                'path': '/',
                'kind': 'folder',
                'name': '/ (Full Dropbox)',
                'urls': {
                    'folders': api_v2_url('nodes/{}/addons/dropbox/folders/'.format(self.owner._id),
                        params={'id': '/'}
                    )
                }
            }]

        client = DropboxClient(self.external_account.oauth_key)
        file_not_found = HTTPError(http.NOT_FOUND, data={
            'message_short': 'File not found',
            'message_long': 'The Dropbox file you requested could not be found.'
        })

        max_retry_error = HTTPError(http.REQUEST_TIMEOUT, data={
            'message_short': 'Request Timeout',
            'message_long': 'Dropbox could not be reached at this time.'
        })

        try:
            metadata = client.metadata(folder_id)
        except ErrorResponse:
            raise file_not_found
        except MaxRetryError:
            raise max_retry_error

        # Raise error if folder was deleted
        if metadata.get('is_deleted'):
            raise file_not_found

        return [
            {
                'addon': 'dropbox',
                'kind': 'folder',
                'id': item['path'],
                'name': item['path'].split('/')[-1],
                'path': item['path'],
                'urls': {
                    'folders': api_v2_url('nodes/{}/addons/box/folders/'.format(self.owner._id),
                        params={'id': item['path']}
                    )
                }
            }
            for item in metadata['contents']
            if item['is_dir']
        ]

    def set_folder(self, folder, auth):
        self.folder = folder
        # Add log to node
        self.nodelogger.log(action='folder_selected', save=True)

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        folder = self.folder
        self.clear_settings()

        if add_log:
            extra = {'folder': folder}
            self.nodelogger.log(action='node_deauthorized', extra=extra, save=True)

        self.clear_auth()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.external_account.oauth_key}

    def serialize_waterbutler_settings(self):
        if not self.folder:
            raise exceptions.AddonError('Folder is not configured')
        return {'folder': self.folder}

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'].strip('/'), provider='dropbox')
        self.owner.add_log(
            'dropbox_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['path'],
                'folder': self.folder,
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    def __repr__(self):
        return u'<DropboxNodeSettings(node_id={self.owner._primary_key!r})>'.format(self=self)

    ##### Callback overrides #####
    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()
