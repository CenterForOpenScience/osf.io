"""

"""

import os
import logging

from framework import fields
from website.addons.base import (
    AddonUserSettingsBase, AddonNodeSettingsBase,
    GuidFile
)
from website.util.permissions import READ

from .api import client
from .exceptions import GitlabError
from .utils import create_user, translate_permissions


logger = logging.getLogger(__name__)


class AddonGitlabUserSettings(AddonUserSettingsBase):

    ########
    # Data #
    ########

    # Account credentials
    user_id = fields.StringField()
    username = fields.StringField()
    password = fields.StringField()

    #############
    # Callbacks #
    #############

    def after_add_addon(self, user):
        create_user(self)


class AddonGitlabNodeSettings(AddonNodeSettingsBase):

    ########
    # Data #
    ########

    creator_osf_id = fields.StringField()
    project_id = fields.StringField()

    #############
    # Callbacks #
    #############

    def after_add_contributor(self, node, added):
        """Add new user to GitLab project.

        """
        user_settings = added.get_addon('gitlab')
        permissions = node.get_permissions(added)
        access_level = translate_permissions(permissions)
        client.addprojectmember(
            self.project_id, user_settings.user_id,
            access_level=access_level
        )

    def after_set_permissions(self, node, user, permissions):
        """Update GitLab permissions.

        """
        user_settings = user.get_addon('gitlab')
        access_level = translate_permissions(permissions)
        client.editprojectmember(
            self.project_id, user_settings.user_id,
            access_level=access_level
        )

    def after_remove_contributor(self, node, removed):
        """Remove user from GitLab project.

        """
        user_settings = removed.get_addon('gitlab')
        client.deleteprojectmember(self.project_id, user_settings.user_id)

    def after_fork(self, node, fork, user, save=True):
        """

        """
        # Call superclass method
        clone, message = super(AddonGitlabNodeSettings, self).after_fork(
            node, fork, user, save=False
        )

        # Get user settings
        user_settings = user.get_or_add_addon('gitlab')

        # Copy project
        copy = client.createcopy(
            self.project_id, user_settings.user_id, fork._id
        )
        if copy['id'] is None:
            raise GitlabError('Could not copy project')
        clone.project_id = copy['id']

        # Optionally save changes
        if save:
            clone.save()

        return clone, message

    def after_register(self, node, registration, user, save=True):
        """

        """
        # Call superclass method
        clone, message = super(AddonGitlabNodeSettings, self).after_register(
            node, registration, user, save=False
        )

        # Get user settings
        user_settings = user.get_or_add_addon('gitlab')

        # Copy project
        copy = client.createcopy(
            self.project_id, user_settings.user_id, registration._id
        )
        if copy['id'] is None:
            raise GitlabError('Could not copy project')
        clone.project_id = copy['id']

        # Grant all contributors read-only permissions
        # TODO: Patch Gitlab so this can be done with one API call
        permission = translate_permissions(READ)
        client.editprojectmember(
            clone.project_id, user_settings.user_id, permission
        )
        for contrib in registration.contributors:
            if contrib == user:
                continue
            contrib_settings = contrib.get_or_add_addon('gitlab')
            client.addprojectmember(
                clone.project_id, contrib_settings.user_id, permission
            )

        # Optionally save changes
        if save:
            clone.save()

        return clone, message

class GitlabGuidFile(GuidFile):

    path = fields.StringField(index=True)

    @property
    def file_url(self):
        if self.path is None:
            raise ValueError('Path field must be defined.')
        return os.path.join('gitlab', 'files', self.path)
