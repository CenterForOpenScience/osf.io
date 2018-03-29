import httplib as http
import logging
import os

from oauthlib.common import generate_token

from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models
from dropbox.dropbox import Dropbox
from dropbox.exceptions import ApiError, DropboxException
from dropbox.files import FolderMetadata
from dropbox.client import DropboxOAuth2Flow
from flask import request
from framework.auth import Auth
from framework.exceptions import HTTPError
from framework.sessions import session
from osf.models.external import ExternalProvider
from osf.models.files import File, Folder, BaseFileNode
from addons.base import exceptions
from addons.dropbox import settings
from addons.dropbox.serializer import DropboxSerializer
from website.util import api_v2_url, web_url_for

logger = logging.getLogger(__name__)


class DropboxFileNode(BaseFileNode):
    _provider = 'dropbox'


class DropboxFolder(DropboxFileNode, Folder):
    pass


class DropboxFile(DropboxFileNode, File):
    @property
    def _hashes(self):
        try:
            return {'Dropbox content_hash': self._history[-1]['extra']['hashes']['dropbox']}
        except (IndexError, KeyError):
            return None


class Provider(ExternalProvider):
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
                'state': generate_token()
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
        ret = self.oauth_flow.start('force_reapprove=true')
        session.save()
        return ret

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

        self.client = Dropbox(access_token)

        info = self.client.users_get_current_account()
        return self._set_external_account(
            user,
            {
                'key': access_token,
                'provider_id': info.account_id,
                'display_name': info.name.display_name,
            }
        )


class UserSettings(BaseOAuthUserSettings):
    """Stores user-specific dropbox information.
    token.
    """
    oauth_provider = Provider
    serializer = DropboxSerializer

    def revoke_remote_oauth_access(self, external_account):
        """Overrides default behavior during external_account deactivation.

        Tells Dropbox to remove the grant for the OSF associated with this account.
        """
        client = Dropbox(external_account.oauth_key)
        try:
            client.auth_token_revoke()
        except DropboxException:
            pass


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = Provider
    serializer = DropboxSerializer

    folder = models.TextField(null=True, blank=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = Provider(self.external_account)
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

        client = Dropbox(self.external_account.oauth_key)

        try:
            folder_id = '' if folder_id == '/' else folder_id
            list_folder = client.files_list_folder(folder_id)
            contents = [x for x in list_folder.entries]
            while list_folder.has_more:
                list_folder = client.files_list_folder_continue(list_folder.cursor)
                contents += [x for x in list_folder.entries]
        except ApiError as error:
            raise HTTPError(http.BAD_REQUEST, data={
                'message_short': error.user_message_text,
                'message_long': error.user_message_text,
            })
        except DropboxException:
            raise HTTPError(http.BAD_REQUEST)

        return [
            {
                'addon': 'dropbox',
                'kind': 'folder',
                'id': item.path_display,
                'name': item.path_display.split('/')[-1],
                'path': item.path_display,
                'urls': {
                    'folders': api_v2_url('nodes/{}/addons/dropbox/folders/'.format(self.owner._id),
                        params={'id': item.path_display}
                    )
                }
            }
            for item in contents
            if isinstance(item, FolderMetadata)
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
        url = self.owner.web_url_for('addon_view_or_download_file',
            path=metadata['path'].strip('/'),
            provider='dropbox'
        )
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
        return u'<NodeSettings(node_id={self.owner._primary_key!r})>'.format(self=self)

    ##### Callback overrides #####
    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()
