# -*- coding: utf-8 -*-
import httplib as http

from addons.base import exceptions
from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models

from framework.auth.decorators import Auth
from framework.exceptions import HTTPError
from framework.sessions import session
from requests_oauthlib import OAuth2Session
from flask import request

from osf.models.external import ExternalProvider
from osf.models.files import File, Folder, BaseFileNode
from oauthlib.oauth2.rfc6749.errors import MissingTokenError
from requests.exceptions import HTTPError as RequestsHTTPError

from addons.weko.client import connect_or_error
from addons.weko.serializer import WEKOSerializer
from addons.weko.utils import WEKONodeLogger
from addons.weko import settings as weko_settings
from website.util import web_url_for, api_v2_url

OAUTH2 = 2

class WEKOProvider(ExternalProvider):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'WEKO'
    short_name = 'weko'
    serializer = WEKOSerializer

    client_id = None
    client_secret = None
    auth_url_base = None
    callback_url = None

    def get_repo_auth_url(self, repoid):
        """The URL to begin the OAuth dance.

        This property method has side effects - it at least adds temporary
        information to the session so that callbacks can be associated with
        the correct user.  For OAuth1, it calls the provider to obtain
        temporary credentials to start the flow.
        """

        # create a dict on the session object if it's not already there
        if session.data.get('oauth_states') is None:
            session.data['oauth_states'] = {}

        repo_settings = weko_settings.REPOSITORIES[repoid]

        assert self._oauth_version == OAUTH2
        # build the URL
        oauth = OAuth2Session(
            repo_settings['client_id'],
            redirect_uri=web_url_for('weko_oauth_callback',
                                     repoid=repoid,
                                     _absolute=True),
            scope=self.default_scopes,
        )

        url, state = oauth.authorization_url(repo_settings['authorize_url'])

        # save state token to the session for confirmation in the callback
        session.data['oauth_states'][self.short_name] = {'state': state}

        return url

    def repo_auth_callback(self, user, repoid, **kwargs):
        """Exchange temporary credentials for permanent credentials

        This is called in the view that handles the user once they are returned
        to the OSF after authenticating on the external service.
        """

        if 'error' in request.args:
            return False

        repo_settings = weko_settings.REPOSITORIES[repoid]

        # make sure the user has temporary credentials for this provider
        try:
            cached_credentials = session.data['oauth_states'][self.short_name]
        except KeyError:
            raise PermissionsError('OAuth flow not recognized.')

        assert self._oauth_version == OAUTH2
        state = request.args.get('state')

        # make sure this is the same user that started the flow
        if cached_credentials.get('state') != state:
            raise PermissionsError('Request token does not match')

        try:
            callback_url = web_url_for('weko_oauth_callback', repoid=repoid,
                                       _absolute=True)
            response = OAuth2Session(
                repo_settings['client_id'],
                redirect_uri=callback_url,
            ).fetch_token(
                repo_settings['access_token_url'],
                client_secret=repo_settings['client_secret'],
                code=request.args.get('code'),
            )
        except (MissingTokenError, RequestsHTTPError):
            raise HTTPError(http.SERVICE_UNAVAILABLE)
        # pre-set as many values as possible for the ``ExternalAccount``
        info = self._default_handle_callback(response)
        # call the hook for subclasses to parse values from the response
        info.update(self.handle_callback(repoid, response))

        return self._set_external_account(user, info)

    def handle_callback(self, repoid, response):
        """View called when the OAuth flow is completed.
        """
        repo_settings = weko_settings.REPOSITORIES[repoid]
        connection = connect_or_error(repo_settings['host'],
                                      response.get('access_token'))
        login_user = connection.get_login_user('unknown')
        return {
            'provider_id': '{}:{}'.format(repoid, login_user),
            'display_name': login_user + '@' + repoid
        }


class WEKOFileNode(BaseFileNode):
    _provider = 'weko'


class WEKOFolder(WEKOFileNode, Folder):
    pass


class WEKOFile(WEKOFileNode, File):
    version_identifier = 'version'


class UserSettings(BaseOAuthUserSettings):
    oauth_provider = WEKOProvider
    serializer = WEKOSerializer


class NodeSettings(BaseStorageAddon, BaseOAuthNodeSettings):
    oauth_provider = WEKOProvider
    serializer = WEKOSerializer

    index_title = models.TextField(blank=True, null=True)
    index_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True)

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = WEKOProvider(self.external_account)
        return self._api

    @property
    def folder_name(self):
        return self.index_title

    @property
    def complete(self):
        return bool(self.has_auth and self.index_id is not None)

    @property
    def folder_id(self):
        return self.index_id

    @property
    def folder_path(self):
        pass

    @property
    def nodelogger(self):
        # TODO: Use this for all log actions
        auth = None
        if self.user_settings:
            auth = Auth(self.user_settings.owner)
        return WEKONodeLogger(
            node=self.owner,
            auth=auth
        )

    def set_folder(self, index, auth=None):
        self.index_id = index.identifier
        self.index_title = index.title

        self.save()

        if auth:
            self.owner.add_log(
                action='weko_index_linked',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                    'dataset': index.title,
                },
                auth=auth,
            )

    def clear_settings(self):
        """Clear selected index"""
        self.index_id = None
        self.index_title = None

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        self.clear_auth()  # Also performs a save

        # Log can't be added without auth
        if add_log and auth:
            node = self.owner
            self.owner.add_log(
                action='weko_node_deauthorized',
                params={
                    'project': node.parent_id,
                    'node': node._id,
                },
                auth=auth,
            )

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        provider_id = self.external_account.provider_id
        login_user = provider_id[provider_id.index(':') + 1:]
        return {'token': self.external_account.oauth_key,
                'user_id': login_user}

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('WEKO is not configured')
        return {
            'host': self.external_account.oauth_key,
            'nid': self.owner._id,
            'url': weko_settings.REPOSITORIES[self.external_account.provider_id.split(':')[0]]['host'],
            'index_id': self.index_id,
            'index_title': self.index_title,
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='weko')
        self.owner.add_log(
            'weko_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'dataset': self.index_title,
                'filename': metadata['materialized'].strip('/'),
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    ##### Callback overrides #####

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()
