"""

"""

import os
import uuid
import logging

from framework import fields
from website.addons.base import (
    AddonUserSettingsBase, AddonNodeSettingsBase,
    GuidFile
)

from .api import client
from .exceptions import GitlabError
from .utils import initialize_repo, translate_permissions


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
        password = str(uuid.uuid4())
        status = client.createuser(
            name=user.fullname,
            username=user._id,
            password=password,
            email=user.username,
        )
        if status:
            self.user_id = status['id']
            self.username = user.fullname
            self.password = password
            self.save()
        else:
            raise GitlabError('Could not create user')


class AddonGitlabNodeSettings(AddonNodeSettingsBase):

    ########
    # Data #
    ########

    creator_osf_id = fields.StringField()
    project_id = fields.StringField()

    #############
    # Callbacks #
    #############

    def after_add_addon(self, node):
        user_settings = node.creator.get_addon('gitlab')
        if not user_settings:
            node.creator.add_addon('gitlab')
            user_settings = node.creator.get_addon('gitlab')
        response = client.createprojectuser(
            user_settings.user_id, node._id
        )
        if response:
            self.creator_osf_id = node.creator._id
            self.project_id = response['id']
            initialize_repo(self)
            self.save()

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
        pass

    def after_register(self, node, registration, user, save=True):
        pass

class GitlabGuidFile(GuidFile):

    path = fields.StringField(index=True)

    @property
    def file_url(self):
        if self.path is None:
            raise ValueError('Path field must be defined.')
        return os.path.join('gitlab', 'files', self.path)
