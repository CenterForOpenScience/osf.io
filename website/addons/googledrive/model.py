# -*- coding: utf-8 -*-
"""Persistence layer for the google drive addon.
"""
import os
import urllib

from modularodm import fields

from framework.auth import Auth
from website.oauth.models import ExternalProvider

from website.addons.base import exceptions
from website.addons.base import StorageAddonBase
from website.addons.base import AddonOAuthNodeSettingsBase, AddonOAuthUserSettingsBase

from website.addons.googledrive import settings as drive_settings
from website.addons.googledrive.serializer import GoogleDriveSerializer
from website.addons.googledrive.client import GoogleAuthClient, GoogleDriveClient
from website.addons.googledrive.utils import GoogleDriveNodeLogger


class GoogleDriveProvider(ExternalProvider):
    name = 'Google Drive'
    short_name = 'googledrive'

    client_id = drive_settings.CLIENT_ID
    client_secret = drive_settings.CLIENT_SECRET

    auth_url_base = '{}{}'.format(drive_settings.OAUTH_BASE_URL, 'auth?access_type=offline&approval_prompt=force')
    callback_url = '{}{}'.format(drive_settings.API_BASE_URL, 'oauth2/v3/token')
    auto_refresh_url = callback_url
    refresh_time = drive_settings.REFRESH_TIME

    default_scopes = drive_settings.OAUTH_SCOPE
    _auth_client = GoogleAuthClient()
    _drive_client = GoogleDriveClient()

    def handle_callback(self, response):
        client = self._auth_client
        info = client.userinfo(response['access_token'])
        return {
            'provider_id': info['sub'],
            'display_name': info['name'],
            'profile_url': info.get('profile', None)
        }

    def fetch_access_token(self, force_refresh=False):
        self.refresh_oauth_key(force=force_refresh)
        return self.account.oauth_key


class GoogleDriveUserSettings(StorageAddonBase, AddonOAuthUserSettingsBase):
    oauth_provider = GoogleDriveProvider
    serializer = GoogleDriveSerializer


class GoogleDriveNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = GoogleDriveProvider
    provider_name = 'googledrive'

    folder_id = fields.StringField(default=None)
    folder_name = fields.StringField(default=None)
    folder_path = fields.StringField()
    serializer = GoogleDriveSerializer

    _api = None

    foreign_user_settings = fields.ForeignField(
        'googledriveusersettings', backref='authorized'
    )

    @property
    def api(self):
        """Authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = GoogleDriveProvider(self.external_account)
        return self._api

    @property
    def complete(self):
        return bool(self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': self.folder_id}
        ))

    @property
    def folder_name(self):
        if not self.folder_id:
            return None

        if self.folder_path != '/':
            # `urllib` does not properly handle unicode.
            # encode input to `str`, decode output back to `unicode`
            return urllib.unquote(os.path.split(self.folder_path)[1].encode('utf-8')).decode('utf-8')
        else:
            return '/ (Full Google Drive)'

    def clear_auth(self):
        self.folder_id = None
        self.folder_path = None
        return super(GoogleDriveNodeSettings, self).clear_auth()

    def set_auth(self, *args, **kwargs):
        self.folder_id = None
        return super(GoogleDriveNodeSettings, self).set_auth(*args, **kwargs)

    def set_target_folder(self, folder, auth):
        """Configure this addon to point to a Google Drive folder

        :param dict folder:
        :param User user:
        """
        self.folder_id = folder['id']
        self.folder_path = folder['path']

        if not self.complete:
            # Tell the user's addon settings that this node is connecting
            self.user_settings.grant_oauth_access(
                node=self.owner,
                external_account=self.external_account,
                metadata={'folder': self.folder_id}
            )
            self.user_settings.save()

        # update this instance
        self.save()

        self.owner.add_log(
            'googledrive_folder_selected',
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'folder': self.folder_name,
            },
            auth=auth,
        )

    @property
    def selected_folder_name(self):
        if self.folder_id is None:
            return ''
        elif self.folder_id == 'root':
            return 'Full Google Drive'
        else:
            return self.folder_name

    def deauthorize(self, auth=None, add_log=True, save=False):
        """Remove user authorization from this node and log the event."""
        node = self.owner

        if add_log:
            extra = {'folder_id': self.folder_id}
            nodelogger = GoogleDriveNodeLogger(node=node, auth=auth)
            nodelogger.log(action="node_deauthorized", extra=extra, save=True)

        self.folder_id = None
        self.user_settings = None
        self.clear_auth()

        if save:
            self.save()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.fetch_access_token()}

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('Folder is not configured')

        return {
            'folder': {
                'id': self.folder_id,
                'name': self.folder_name,
                'path': self.folder_path
            }
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='googledrive')

        self.owner.add_log(
            'googledrive_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['path'],
                'folder': self.folder_path,

                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    def fetch_access_token(self):
        return self.api.fetch_access_token()

    # #### Callback overrides #####

    def before_register_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        registration.
        """
        category, title = node.project_or_component, node.title
        if self.user_settings and self.user_settings.has_auth:
            return (
                u'The contents of Google Drive add-ons cannot be registered at this time; '
                u'the Google Drive folder linked to this {category} will not be included '
                u'as part of this registration.'
            ).format(**locals())

    # backwards compatibility
    before_register = before_register_message

    def before_remove_contributor_message(self, node, removed):
        """Return warning text to display if removed contributor is the user
        who authorized the GoogleDrive addon
        """
        if self.user_settings and self.user_settings.owner == removed:
            category = node.project_or_component
            name = removed.fullname
            return (u'The Google Drive add-on for this {category} is authenticated by {name}. '
                    'Removing this user will also remove write access to Google Drive '
                    'unless another contributor re-authenticates the add-on.'
                    ).format(**locals())

    # backwards compatibility
    before_remove_contributor = before_remove_contributor_message

    def after_fork(self, node, fork, user, save=True):
        """After forking, copy user settings if the user is the one who authorized
        the addon.

        :return: A tuple of the form (cloned_settings, message)
        """
        clone, _ = super(GoogleDriveNodeSettings, self).after_fork(
            node=node, fork=fork, user=user, save=False
        )

        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            message = 'Google Drive authorization copied to fork.'
        else:
            message = ('Google Drive authorization not copied to forked {cat}. You may '
                       'authorize this fork on the <u><a href="{url}">Settings</a></u> '
                       'page.').format(
                url=fork.web_url_for('node_setting'),
                cat=fork.project_or_component
            )
        if save:
            clone.save()
        return clone, message

    def after_remove_contributor(self, node, removed, auth=None):
        """If the removed contributor was the user who authorized the GoogleDrive
        addon, remove the auth credentials from this node.
        Return the message text that will be displayed to the user.
        """
        if self.user_settings and self.user_settings.owner == removed:

            # Delete OAuth tokens
            self.user_settings = None
            self.save()
            message = (
                u'Because the Google Drive add-on for {category} "{title}" was '
                u'authenticated by {user}, authentication information has been deleted.'
            ).format(category=node.category_display, title=node.title, user=removed.fullname)

            if not auth or auth.user != removed:
                url = node.web_url_for('node_setting')
                message += (
                    u' You can re-authenticate on the <u><a href="{url}">Settings</a></u> page.'
                ).format(url=url)
            return message

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True, save=True)
