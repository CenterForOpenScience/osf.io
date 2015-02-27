# -*- coding: utf-8 -*-
"""Persistence layer for the google drive addon.
"""
import os
import base64
from urllib import unquote
from datetime import datetime

from modularodm import fields, Q
from modularodm.exceptions import ModularOdmException

from framework.auth import Auth
from framework.mongo import StoredObject

from website import settings
from website.addons.base import exceptions
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase, GuidFile

from website.addons.googledrive.client import GoogleAuthClient
from website.addons.googledrive import settings as drive_settings
from website.addons.googledrive.utils import GoogleDriveNodeLogger


class GoogleDriveGuidFile(GuidFile):
    path = fields.StringField(index=True)

    @property
    def waterbutler_path(self):
        return self.path.replace(self.folder, '', 1)

    @property
    def provider(self):
        return 'googledrive'

    @property
    def version_identifier(self):
        return 'revision'

    @property
    def file_name(self):
        if self.revision:
            return '{0}_{1}_{2}.html'.format(self._id, self.revision, base64.b64encode(self.folder))
        return '{0}_{1}_{2}.html'.format(self._id, self.unique_identifier, base64.b64encode(self.folder))

    @property
    def mfr_temp_path(self):
        """Files names from Google Docs metadata doesn't necessarily correspond
        to download file names. Use the `downloadExt` field in the Docs metadata
        to save the temporary file with the appropriate extension.
        """
        ext = (
            self._metadata_cache['extra'].get('downloadExt') or
            os.path.splitext(self.name)[-1]
        )
        return os.path.join(
            settings.MFR_TEMP_PATH,
            self.node._id,
            self.provider,
            # Attempt to keep the original extension of the file for MFR detection
            self.file_name + ext,
        )

    @property
    def folder(self):
        folder = self.node.get_addon('googledrive').folder_path
        if folder == '/':
            return ''
        return '/' + folder

    @property
    def unique_identifier(self):
        return self._metadata_cache['extra']['revisionId']

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


class GoogleDriveOAuthSettings(StoredObject):
    """
    this model address the problem if we have two osf user link
    to the same google drive user and their access token conflicts issue
    """

    # google drive user id, for example, "4974056"
    user_id = fields.StringField(primary=True, required=True)
    # google drive user name this is the user's login
    username = fields.StringField()
    access_token = fields.StringField()
    refresh_token = fields.StringField()
    expires_at = fields.DateTimeField()

    def fetch_access_token(self):
        self.refresh_access_token()
        return self.access_token

    def refresh_access_token(self, force=False):
        if self._needs_refresh() or force:
            client = GoogleAuthClient()
            token = client.refresh(self.access_token, self.refresh_token)

            self.access_token = token['access_token']
            self.refresh_token = token['refresh_token']
            self.expires_at = datetime.utcfromtimestamp(token['expires_at'])
            self.save()

    def revoke_access_token(self):
        # if there is only one osf user linked to this google drive user oauth, revoke the token,
        # otherwise, disconnect the osf user from the googledriveoauthsettings
        if len(self.googledriveusersettings__accessed) <= 1:
            client = GoogleAuthClient()
            try:
                client.revoke(self.access_token)
            except:
                # no need to fail, revoke is opportunistic
                pass

            # remove the object as its the last instance.
            GoogleDriveOAuthSettings.remove_one(self)

    def _needs_refresh(self):
        if self.expires_at is None:
            return False
        return (self.expires_at - datetime.utcnow()).total_seconds() < drive_settings.REFRESH_TIME


class GoogleDriveUserSettings(AddonUserSettingsBase):
    """Stores user-specific information, including the Oauth access
    token.
    """
    oauth_settings = fields.ForeignField(
        'googledriveoauthsettings', backref='accessed'
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
        self.oauth_settings.username = val

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

    def clear(self):
        if self.oauth_settings:
            self.oauth_settings.revoke_access_token()
            self.oauth_settings = None
            self.save()

        for node_settings in self.googledrivenodesettings__authorized:
            node_settings.deauthorize(Auth(self.owner))
            node_settings.save()

    def save(self, *args, **kwargs):
        if self.oauth_settings:
            self.oauth_settings.save()
        return super(GoogleDriveUserSettings, self).save(*args, **kwargs)

    def delete(self, save=True):
        self.clear()
        super(GoogleDriveUserSettings, self).delete(save)

    def __repr__(self):
        return u'<GoogleDriveUserSettings(user={self.owner.username!r})>'.format(self=self)


class GoogleDriveNodeSettings(AddonNodeSettingsBase):

    folder_id = fields.StringField(default=None)
    folder_path = fields.StringField(default=None)

    user_settings = fields.ForeignField(
        'googledriveusersettings', backref='authorized'
    )

    @property
    def folder_name(self):
        if not self.folder_id:
            return None

        if self.folder_path != '/':
            return unquote(os.path.split(self.folder_path)[1])

        return '/ (Full Google Drive)'

    @property
    def has_auth(self):
        """Whether an access token is associated with this node."""
        return bool(self.user_settings and self.user_settings.has_auth)

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        if add_log:
            extra = {'folder': self.folder_name}
            nodelogger = GoogleDriveNodeLogger(node=self.owner, auth=auth)
            nodelogger.log(action="node_deauthorized", extra=extra, save=True)

        self.folder_id = None
        self.folder_path = None
        self.user_settings = None

        self.save()

    def set_folder(self, folder, auth, add_log=True):
        self.folder_id = folder['id']
        self.folder_path = folder['path']

        # Add log to node
        if add_log:
            nodelogger = GoogleDriveNodeLogger(node=self.owner, auth=auth)
            nodelogger.log(action="folder_selected", save=True)

    def set_user_auth(self, user_settings):
        """Import a user's GoogleDrive authentication and create a NodeLog.

        :param GoogleDriveUserSettings user_settings: The user settings to link.
        """
        self.user_settings = user_settings
        nodelogger = GoogleDriveNodeLogger(node=self.owner, auth=Auth(user_settings.owner))
        nodelogger.log(action="node_authorized", save=True)

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.user_settings.fetch_access_token()}

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
        # cleaned_path = clean_path(metadata['path'])
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

    def find_or_create_file_guid(self, path):
        path = os.path.join(self.folder_path, path.lstrip('/'))
        if self.folder_path != '/':
            path = '/' + path

        return GoogleDriveGuidFile.get_or_create(self.owner, path)

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

    def before_fork_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        fork.
        """
        category = node.project_or_component
        if self.user_settings and self.user_settings.owner == user:
            return (u'Because you have authorized the Google Drive add-on for this '
                    '{category}, forking it will also transfer your authentication token to '
                    'the forked {category}.').format(category=category)

        else:
            return (u'Because the Google Drive add-on has been authorized by a different '
                    'user, forking it will not transfer authentication token to the forked '
                    '{category}.').format(category=category)

    # backwards compatibility
    before_fork = before_fork_message

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
                       'authorize this fork on the <a href="{url}">Settings</a>'
                       'page.').format(
                url=fork.web_url_for('node_setting'),
                cat=fork.project_or_component
            )
        if save:
            clone.save()
        return clone, message

    def after_remove_contributor(self, node, removed):
        """If the removed contributor was the user who authorized the GoogleDrive
        addon, remove the auth credentials from this node.
        Return the message text that will be displayed to the user.
        """
        if self.user_settings and self.user_settings.owner == removed:
            self.user_settings = None
            self.save()
            name = removed.fullname
            url = node.web_url_for('node_setting')
            return ('Because the Google Drive add-on for this project was authenticated'
                    'by {name}, authentication information has been deleted. You '
                    'can re-authenticate on the <a href="{url}">Settings</a> page'
                    ).format(**locals())

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()
