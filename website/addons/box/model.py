# -*- coding: utf-8 -*-
import os
import time
import logging
import httplib as http
from datetime import datetime

import furl
import requests
from flask import request, redirect
from box import CredentialsV2, refresh_v2_token, BoxClient
from box.client import BoxClientException
from modularodm import fields, Q, StoredObject
from modularodm.exceptions import ModularOdmException
from werkzeug.wrappers import BaseResponse

from framework.auth import Auth
from framework.exceptions import HTTPError
from framework.sessions import session
from framework.auth.decorators import must_be_logged_in
from framework.status import push_status_message as flash

from website.util import api_url_for
from website.util import web_url_for
from website import security
from website.project.model import Node
from website.project.decorators import must_have_addon

from website.addons.base import exceptions
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase, GuidFile

from website.addons.box import settings
from website.addons.box.utils import BoxNodeLogger
from website.oauth.models import ExternalProvider
from website.addons.box.utils import handle_box_error

logger = logging.getLogger(__name__)


class Box(ExternalProvider):
    name = 'Box'
    short_name = 'box'

    client_id = settings.BOX_KEY
    client_secret = settings.BOX_SECRET

    auth_url_base = settings.BOX_OAUTH_AUTH_ENDPOINT
    callback_url = settings.BOX_OAUTH_TOKEN_ENDPOINT
    default_scopes = ['all']

    def get_auth_flow(self, csrf_token):
        url = furl.furl(settings.BOX_OAUTH_AUTH_ENDPOINT)

        url.args = {
            'state': csrf_token,
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': api_url_for('box_oauth_finish', _absolute=True),
        }

        return url.url

    def finish_auth(self):
        """View helper for finishing the Box Oauth2 flow. Returns the
        access_token, user_id, and url_state.

        Handles various errors that may be raised by the Box client.
        """
        if 'error' in request.args:
            self.handle_box_error(error=request.args['error'], msg=request.args['error_description'])

        # Should always be defined
        code = request.args['code']
        # Default to empty string over None because of below assertion
        state = request.args.get('state', '')

        if state != session.data.pop('box_oauth_state', None):
            raise HTTPError(http.FORBIDDEN)

        data = {
            'code': code,
            'client_id': settings.BOX_KEY,
            'grant_type': 'authorization_code',
            'client_secret': settings.BOX_SECRET,
        }

        response = requests.post(settings.BOX_OAUTH_TOKEN_ENDPOINT, data)
        result = response.json()

        if 'error' in result:
            handle_box_error(
                error=request.args['error'],
                msg=request.args['error_description'])

        return result

    @must_be_logged_in
    def box_oauth_start(self, auth, **kwargs):
        user = auth.user
        # Store the node ID on the session in order to get the correct redirect URL
        # upon finishing the flow
        nid = kwargs.get('nid') or kwargs.get('pid')

        node = Node.load(nid)

        if node and not node.is_contributor(user):
            raise HTTPError(http.FORBIDDEN)

        csrf_token = security.random_string(10)
        session.data['box_oauth_state'] = csrf_token

        if nid:
            session.data['box_auth_nid'] = nid

        # If user has already authorized box, flash error message
        if user.has_addon('box') and user.get_addon('box').has_auth:
            flash('You have already authorized Box for this account', 'warning')
            return redirect(web_url_for('user_addons'))

        return redirect(self.get_auth_flow(csrf_token))

    @must_be_logged_in
    def box_oauth_finish(self, auth, **kwargs):
        """View called when the Oauth flow is completed. Adds a new BoxUserSettings
        record to the user and saves the user's access token and account info.
        """
        user = auth.user
        node = Node.load(session.data.pop('box_auth_nid', None))

        # Handle request cancellations from Box's API
        if request.args.get('error'):
            flash('Box authorization request cancelled.')
            if node:
                return redirect(node.web_url_for('node_setting'))
            return redirect(web_url_for('user_addons'))

        result = self.finish_auth()

        # If result is a redirect response, follow the redirect
        if isinstance(result, BaseResponse):
            return result

        client = BoxClient(CredentialsV2(
            result['access_token'],
            result['refresh_token'],
            settings.BOX_KEY,
            settings.BOX_SECRET,
        ))

        about = client.get_user_info()
        oauth_settings = BoxOAuthSettings.load(about['id'])

        if not oauth_settings:
            oauth_settings = BoxOAuthSettings(user_id=about['id'], username=about['name'])
            oauth_settings.save()

        oauth_settings.refresh_token = result['refresh_token']
        oauth_settings.access_token = result['access_token']
        oauth_settings.expires_at = datetime.utcfromtimestamp(time.time() + 3600)

        # Make sure user has box enabled
        user.add_addon('box')
        user.save()

        user_settings = user.get_addon('box')
        user_settings.oauth_settings = oauth_settings

        user_settings.save()

        flash('Successfully authorized Box', 'success')

        if node:
            # Automatically use newly-created auth
            if node.has_addon('box'):
                node_addon = node.get_addon('box')
                node_addon.set_user_auth(user_settings)
                node_addon.save()
            return redirect(node.web_url_for('node_setting'))
        return redirect(web_url_for('user_addons'))

    @must_be_logged_in
    @must_have_addon('box', 'user')
    def box_oauth_delete_user(self, user_addon, auth, **kwargs):
        """View for deauthorizing Box."""
        user_addon.clear()
        user_addon.save()

    @must_be_logged_in
    @must_have_addon('box', 'user')
    def box_user_config_get(self, user_addon, auth, **kwargs):
        """View for getting a JSON representation of the logged-in user's
        Box user settings.
        """
        urls = {
            'create': api_url_for('box_oauth_start_user'),
            'delete': api_url_for('box_oauth_delete_user')
        }
        valid_credentials = True

        if user_addon.has_auth:
            try:
                client = self.client
                client.get_user_info()
            except BoxClientException:
                valid_credentials = False

        return {
            'result': {
                'urls': urls,
                'boxName': user_addon.username,
                'userHasAuth': user_addon.has_auth,
                'validCredentials': valid_credentials,
                'nNodesAuthorized': len(user_addon.nodes_authorized),
            },
        }


class BoxFile(GuidFile):
    """A Box file model with a GUID. Created lazily upon viewing a
    file's detail page.
    """

    #: Full path to the file, e.g. 'My Pictures/foo.png'
    path = fields.StringField(required=True, index=True)

    @property
    def waterbutler_path(self):
        if not self.path.startswith('/'):
            return '/{}'.format(self.path)
        return self.path

    @property
    def provider(self):
        return 'box'

    @property
    def version_identifier(self):
        return 'revision'

    @property
    def unique_identifier(self):
        return self._metadata_cache['extra'].get('etag') or self._metadata_cache['version']

    @classmethod
    def get_or_create(cls, node, path):
        """Get or create a new file record. Return a tuple of the form (obj, created)
        """
        try:
            new = cls.find_one(
                Q('node', 'eq', node) &
                Q('path', 'eq', path)
            )
            created = False
        except ModularOdmException:
            # Create new
            new = cls(node=node, path=path)
            new.save()
            created = True
        return new, created


class BoxOAuthSettings(StoredObject):
    """
    this model address the problem if we have two osf user link
    to the same box user and their access token conflicts issue
    """
    name = 'Box'

    # Box user id, for example, "4974056"
    user_id = fields.StringField(primary=True, required=True)
    # Box user name this is the user's login
    username = fields.StringField()
    access_token = fields.StringField()
    refresh_token = fields.StringField()
    expires_at = fields.DateTimeField()

    @property
    def get_client(self):
        if self._needs_refresh():
            self.refresh_access_token()

        return BoxClient(
            self.get_credentialsv2()
        )

    def fetch_access_token(self):
        self.refresh_access_token()
        return self.access_token

    def get_credentialsv2(self):
        return CredentialsV2(
            self.access_token,
            self.refresh_token,
            settings.BOX_KEY,
            settings.BOX_SECRET
        )

    def refresh_access_token(self, force=False):
        # Ensure that most recent tokens are loaded from the database. Needed
        # in case another concurrent request has already changed the tokens.
        if self._is_loaded:
            try:
                self.reload()
            except:
                pass
        if self._needs_refresh() or force:
            token = refresh_v2_token(settings.BOX_KEY, settings.BOX_SECRET, self.refresh_token)

            self.access_token = token['access_token']
            self.refresh_token = token.get('refresh_token', self.refresh_token)
            self.expires_at = datetime.utcfromtimestamp(time.time() + token['expires_in'])
            self.save()

    def revoke_access_token(self):
        # if there is only one osf user linked to this box user oauth, revoke the token,
        # otherwise, disconnect the osf user from the boxoauthsettings
        if len(self.boxusersettings__accessed) <= 1:
            url = furl.furl('https://www.box.com/api/oauth2/revoke/')
            url.args = {
                'token': self.access_token,
                'client_id': settings.BOX_KEY,
                'client_secret': settings.BOX_SECRET,
            }
            # no need to fail, revoke is opportunistic
            requests.post(url.url)

            # remove the object as its the last instance.
            BoxOAuthSettings.remove_one(self)

    def _needs_refresh(self):
        if self.expires_at is None:
            return False
        return (self.expires_at - datetime.utcnow()).total_seconds() < settings.REFRESH_TIME


class BoxUserSettings(AddonOAuthUserSettingsBase):
    """Stores user-specific box information, including the Oauth access
    token.
    """
    oauth_provider = Box
    oauth_grants = fields.DictionaryField()
    oauth_settings = fields.ForeignField(
        'boxoauthsettings', backref='accessed'
    )

    @property
    def user_id(self):
        if self.oauth_settings:
            return self.oauth_settings.user_id
        return None

    @user_id.setter
    def user_id(self, val):
        self.oauth_settings.user_id = val

    @property
    def username(self):
        if self.oauth_settings:
            return self.oauth_settings.username
        return None

    @username.setter
    def username(self, val):
        self.oauth_settings.name = val

    @property
    def access_token(self):
        if self.oauth_settings:
            return self.oauth_settings.access_token
        return None

    @access_token.setter
    def access_token(self, val):
        self.oauth_settings.access_token = val

    @property
    def refresh_token(self):
        if self.oauth_settings:
            return self.oauth_settings.refresh_token
        return None

    @refresh_token.setter
    def refresh_token(self, val):
        self.oauth_settings.refresh_token = val

    @property
    def expires_at(self):
        if self.oauth_settings:
            return self.oauth_settings.expires_at
        return None

    @expires_at.setter
    def expires_at(self, val):
        self.oauth_settings.expires_at = val

    @property
    def has_auth(self):
        if self.oauth_settings:
            return self.oauth_settings.access_token is not None
        return False

    def fetch_access_token(self):
        if self.oauth_settings:
            return self.oauth_settings.fetch_access_token()
        return None

    def delete(self, save=True):
        self.clear()
        super(BoxUserSettings, self).delete(save)

    def clear(self):
        """Clear settings and deauthorize any associated nodes."""
        if self.oauth_settings:
            self.oauth_settings.revoke_access_token()
            self.oauth_settings = None
            self.save()

        for node_settings in self.boxnodesettings__authorized:
            node_settings.deauthorize(Auth(self.owner))
            node_settings.save()

    def get_credentialsv2(self):
        if not self.has_auth:
            return None
        return self.oauth_settings.get_credentialsv2()

    def save(self, *args, **kwargs):
        if self.oauth_settings:
            self.oauth_settings.save()
        return super(BoxUserSettings, self).save(*args, **kwargs)

    def __repr__(self):
        return u'<BoxUserSettings(user={self.owner.username!r})>'.format(self=self)


class BoxNodeSettings(AddonOAuthNodeSettingsBase):
    oauth_provider = Box

    user_settings = fields.ForeignField(
        'boxusersettings', backref='authorized'
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
            self._api = Box()
            self._api.account = self.external_account
        return self._api

    @property
    def display_name(self):
        return '{0}: {1}'.format(self.config.full_name, self.folder_id)

    @property
    def has_auth(self):
        """Whether an access token is associated with this node."""
        return bool(self.user_settings and self.user_settings.has_auth)

    def fetch_folder_name(self):
        self._update_folder_data()
        return self.folder_name

    def fetch_full_folder_path(self):
        self._update_folder_data()
        return self.folder_path

    def _update_folder_data(self):
        if self.folder_id is None:
            return None

        if not self._folder_data:
            try:
                client = self.user_settings.oauth_settings.get_client  # get_client_from_user_settings(self.user_settings)
                self._folder_data = client.get_folder(self.folder_id)
            except BoxClientException:
                return

            self.folder_name = self._folder_data['name']
            self.folder_path = '/'.join(
                [x['name'] for x in self._folder_data['path_collection']['entries']]
                + [self.fetch_folder_name()]
            )
            self.save()

    def set_folder(self, folder_id, auth):
        self.folder_id = str(folder_id)
        self.save()
        # Add log to node
        nodelogger = BoxNodeLogger(node=self.owner, auth=auth)
        nodelogger.log(action="folder_selected", save=True)

    def set_user_auth(self, user_settings):
        """Import a user's Box authentication and create a NodeLog.

        :param BoxUserSettings user_settings: The user settings to link.
        """
        self.user_settings = user_settings
        nodelogger = BoxNodeLogger(node=self.owner, auth=Auth(user_settings.owner))
        nodelogger.log(action="node_authorized", save=True)

    def find_or_create_file_guid(self, path):
        return BoxFile.get_or_create(self.owner, path)

    # TODO: Is this used? If not, remove this and perhaps remove the 'deleted' field
    def delete(self, save=True):
        self.deauthorize(add_log=False)
        super(BoxNodeSettings, self).delete(save)

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        node = self.owner

        if add_log:
            extra = {'folder_id': self.folder_id}
            nodelogger = BoxNodeLogger(node=node, auth=auth)
            nodelogger.log(action="node_deauthorized", extra=extra, save=True)

        self.folder_id = None
        self.user_settings = None

        self.save()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        try:
            return {'token': self.user_settings.fetch_access_token()}
        except BoxClientException as error:
            return HTTPError(error.status_code)

    def serialize_waterbutler_settings(self):
        if self.folder_id is None:
            raise exceptions.AddonError('Folder is not configured')
        return {'folder': self.folder_id}

    def create_waterbutler_log(self, auth, action, metadata):
        path = metadata['path']
        try:
            full_path = metadata['extra']['fullPath']
        except KeyError:
            full_path = None
        self.owner.add_log(
            'box_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': os.path.join(self.folder_id, path),
                'name': os.path.split(metadata['path'])[-1],
                'folder': self.folder_id,
                'urls': {
                    'view': self.owner.web_url_for('addon_view_or_download_file', provider='box', action='view', path=path),
                    'download': self.owner.web_url_for('addon_view_or_download_file', provider='box', action='download', path=path),
                },
                'fullPath': full_path
            },
        )

    ##### Callback overrides #####

    def before_register_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        registration.
        """
        category = node.project_or_component
        if self.user_settings and self.user_settings.has_auth:
            return (
                u'The contents of Box add-ons cannot be registered at this time; '
                u'the Box folder linked to this {category} will not be included '
                u'as part of this registration.'
            ).format(**locals())

    # backwards compatibility
    before_register = before_register_message

    def before_fork_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        fork.
        """
        category = node.project_or_component
        if self.user_settings and self.user_settings.owner == user:
            return (
                u'Because you have authorized the Box add-on for this '
                '{category}, forking it will also transfer your authentication token to '
                'the forked {category}.'
            ).format(category=category)
        else:
            return (
                u'Because the Box add-on has been authorized by a different '
                'user, forking it will not transfer authentication token to the forked '
                '{category}.'
            ).format(category=category)

    # backwards compatibility
    before_fork = before_fork_message

    def before_remove_contributor_message(self, node, removed):
        """Return warning text to display if removed contributor is the user
        who authorized the Box addon
        """
        if self.user_settings and self.user_settings.owner == removed:
            category = node.project_or_component
            name = removed.fullname
            return (
                u'The Box add-on for this {category} is authenticated by {name}. '
                'Removing this user will also remove write access to Box '
                'unless another contributor re-authenticates the add-on.'
            ).format(**locals())

    # backwards compatibility
    before_remove_contributor = before_remove_contributor_message

    def after_fork(self, node, fork, user, save=True):
        """After forking, copy user settings if the user is the one who authorized
        the addon.

        :return: A tuple of the form (cloned_settings, message)
        """
        clone, _ = super(BoxNodeSettings, self).after_fork(
            node=node, fork=fork, user=user, save=False
        )

        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            message = (
                'Box authorization copied to forked {cat}.'
            ).format(cat=fork.project_or_component)
        else:
            message = (
                u'Box authorization not copied to forked {cat}. You may '
                'authorize this fork on the <a href="{url}">Settings</a> '
                'page.'
            ).format(
                url=fork.web_url_for('node_setting'),
                cat=fork.project_or_component
            )
        if save:
            clone.save()
        return clone, message

    def after_remove_contributor(self, node, removed):
        """If the removed contributor was the user who authorized the Box
        addon, remove the auth credentials from this node.
        Return the message text that will be displayed to the user.
        """
        if self.user_settings and self.user_settings.owner == removed:
            self.user_settings = None
            self.save()
            name = removed.fullname
            url = node.web_url_for('node_setting')
            return (
                u'Because the Box add-on for this project was authenticated'
                'by {name}, authentication information has been deleted. You '
                'can re-authenticate on the <a href="{url}">Settings</a> page'
            ).format(**locals())

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()
