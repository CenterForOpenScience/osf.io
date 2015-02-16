# -*- coding: utf-8 -*-
"""Persistence layer for the gdrive addon.
"""
import os
import furl

from website.addons.base import GuidFile
from modularodm import fields
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from .utils import clean_path
from website.addons.base import exceptions


class AddonGdriveGuidFile(GuidFile):

    path = fields.StringField(index=True)

    @property
    def file_url(self):
        if self.path is None:
            raise ValueError('Path field must be defined.')
        return os.path.join('gdrive', 'file', self.path)


class AddonGdriveUserSettings(AddonUserSettingsBase):
    """Stores user-specific information, including the Oauth access
    token.
    """
    access_token = fields.StringField(required=False)
    # TODO

    @property
    def has_auth(self):
        return bool(self.access_token)

    def clear(self):
        self.access_token = None
        return self

class AddonGdriveNodeSettings(AddonNodeSettingsBase):

    user_settings = fields.ForeignField(
        'addongdriveusersettings', backref='authorized'
    )

    folder = fields.StringField(default=None)
    folderId= fields.StringField(default=None)

    @property
    def has_auth(self):
        """Whether an access token is associated with this node."""
        return bool(self.user_settings and self.user_settings.has_auth)

    def deauthorize(self, auth):
        """Remove user authorization from this node and log the event."""
        # TODO: Any other addon-specific settings should be removed here.
        node = self.owner
        self.user_settings = None
        self.owner.add_log(
            action='gdrive_node_deauthorized',
            params={
                'project': node.parent_id,
                'node': node._id,
            },
            auth=auth,
        )

    def set_folder(self, folder, auth):
        self.folder = folder
        #TODO : Add log to node


    def set_user_auth(self, user_settings):
        """Import a user's GDrive authentication and create a NodeLog.

        :param AddonGdriveUserSettings user_settings: The user settings to link.
        """
        self.user_settings = user_settings

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.user_settings.access_token}

    def serialize_waterbutler_settings(self):
        if not self.folder:
            raise exceptions.AddonError('Folder is not configured')
        return {'folder': self.folder}

    def create_waterbutler_log(self, auth, action, metadata):
        cleaned_path = clean_path(os.path.join(self.folder, metadata['path']))
        self.owner.add_log(
            'gdrive_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': cleaned_path,
                'folder': self.folder,

                'urls': {
                    'view': self.owner.web_url_for('gdrive_view_file', path=cleaned_path), #TODO
                    'download': self.owner.web_url_for('dropbox_download', path=cleaned_path),#TODO
                },
            },
        )

    def get_waterbutler_render_url(self, path, rev=None, **kwargs):

        url = furl.furl(self.owner.web_url_for('gdrive_view_file', path=path))

        if rev:
            url.args['rev'] = rev

        return url.url


    ##### Callback overrides #####

    def before_register_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        registration.
        """
        category, title = node.project_or_component, node.title
        if self.user_settings and self.user_settings.has_auth:
            # TODO:
            pass

    # backwards compatibility
    before_register = before_register_message

    def before_fork_message(self, node, user):
        """Return warning text to display if user auth will be copied to a
        fork.
        """
        # TODO
        pass

    # backwards compatibility
    before_fork = before_fork_message

    def before_remove_contributor_message(self, node, removed):
        """Return warning text to display if removed contributor is the user
        who authorized the Gdrive addon
        """
        if self.user_settings and self.user_settings.owner == removed:
            # TODO
            pass

    # backwards compatibility
    before_remove_contributor = before_remove_contributor_message

    def after_register(self, node, registration, user, save=True):
        """After registering a node, copy the user settings and save the
        chosen folder.

        :return: A tuple of the form (cloned_settings, message)
        """
        clone, message = super(AddonGdriveNodeSettings, self).after_register(
            node, registration, user, save=False
        )
        # Copy user_settings and add registration data
        if self.has_auth and self.folder is not None:
            clone.user_settings = self.user_settings
            clone.registration_data['folder'] = self.folder
        if save:
            clone.save()
        return clone, message

    def after_fork(self, node, fork, user, save=True):
        """After forking, copy user settings if the user is the one who authorized
        the addon.

        :return: A tuple of the form (cloned_settings, message)
        """
        clone, _ = super(AddonGdriveNodeSettings, self).after_fork(
            node=node, fork=fork, user=user, save=False
        )

        if self.user_settings and self.user_settings.owner == user:
            clone.user_settings = self.user_settings
            message = 'Google Drive authorization copied to fork.'
        else:
            message = ('Google Drive authorization not copied to fork. You may '
                        'authorize this fork on the <a href="{url}">Settings</a>'
                        'page.').format(
                        url=fork.web_url_for('node_setting'))
        if save:
            clone.save()
        return clone, message

    def after_remove_contributor(self, node, removed):
        """If the removed contributor was the user who authorized the Gdrive
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
