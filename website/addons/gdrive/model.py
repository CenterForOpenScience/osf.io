# -*- coding: utf-8 -*-
"""Persistence layer for the gdrive addon.
"""

from modularodm import fields
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase


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

    def set_user_auth(self, user_settings):
        """Import a user's GDrive authentication and create a NodeLog.

        :param AddonGdriveUserSettings user_settings: The user settings to link.
        """
        self.user_settings = user_settings

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
        clone, message = super(GdriveNodeSettings, self).after_register(
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
        clone, _ = super(GdriveNodeSettings, self).after_fork(
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
