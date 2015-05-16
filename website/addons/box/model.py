# -*- coding: utf-8 -*-
import os
import time
import logging
import httplib as http
from datetime import datetime

import pymongo
import requests
from flask import request, redirect
from box import CredentialsV2, BoxClient
from box.client import BoxClientException
from modularodm import fields
from werkzeug.wrappers import BaseResponse

from framework.auth import Auth
from framework.exceptions import HTTPError
from framework.sessions import session
from framework.auth.decorators import must_be_logged_in
from framework.status import push_status_message as flash

from website.util import api_url_for
from website.util import web_url_for
from website.project.model import Node
from website.project.decorators import must_have_addon

from website.addons.base import exceptions
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase, GuidFile

from website.addons.box import settings
from website.addons.box.utils import BoxNodeLogger, refresh_oauth_key
from website.addons.box.serializer import BoxSerializer
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
    default_scopes = ['root_readwrite']

    def handle_callback(self, response):
        """View called when the Oauth flow is completed. Adds a new BoxUserSettings
        record to the user and saves the user's access token and account info.
        """

        client = BoxClient(CredentialsV2(
            response['access_token'],
            response['refresh_token'],
            settings.BOX_KEY,
            settings.BOX_SECRET,
        ))

        about = client.get_user_info()

        url = 'https://app.box.com/profile/' + about['id']

        return {
            'provider_id': about['id'],
            'display_name': about['name'],
            'profile_url': url
        }

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
    __indices__ = [
        {
            'key_or_list': [
                ('node', pymongo.ASCENDING),
                ('path', pymongo.ASCENDING),
            ],
            'unique': True,
        }
    ]
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


class BoxUserSettings(AddonOAuthUserSettingsBase):
    """Stores user-specific box information
    """
    oauth_provider = Box
    serializer = BoxSerializer


class BoxNodeSettings(AddonOAuthNodeSettingsBase):
    oauth_provider = Box
    serializer = BoxSerializer

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

    @property
    def complete(self):
        return bool(self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
        ))

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
                refresh_oauth_key(self.external_account)
                client = BoxClient(self.external_account.oauth_key)
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
        self._update_folder_data()
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
        return BoxFile.get_or_create(node=self.owner, path=path)

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
        self._update_folder_data()
        self.user_settings = None

        self.save()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        try:
            refresh_oauth_key(self.external_account)
            return {'token': self.external_account.oauth_key}
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

    def after_remove_contributor(self, node, removed, auth=None):
        """If the removed contributor was the user who authorized the Box
        addon, remove the auth credentials from this node.
        Return the message text that will be displayed to the user.
        """

        if self.user_settings and self.user_settings.owner == removed:

            self.user_settings = None
            self.save()
            message = (
                u'Because the Box add-on for {category} "{title}" was authenticated '
                u'by {user}, authentication information has been deleted.'
            ).format(
                category=node.category_display,
                title=node.title,
                user=removed.fullname
            )

            if not auth or auth.user != removed:
                url = node.web_url_for('node_setting')
                message += (
                    u' You can re-authenticate on the <a href="{url}">Settings</a> page.'
                ).format(url=url)
            #
            return message

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()
