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
from .utils import translate_permissions


logger = logging.getLogger(__name__)


class AddonGitlabUserSettings(AddonUserSettingsBase):

    ########
    # Data #
    ########

    # Account credentials
    user_id = fields.StringField()
    username = fields.StringField()
    password = fields.StringField()

    # SSH keys for direct access to GitLab
    # [
    #   {'id': 1, 'title': 'public', 'key': 'ssh-rsa...'}
    #   {'id': 2, 'title': 'public2', 'key': 'ssh-rsa...'}
    # ]
    ssh_keys = fields.DictionaryField(list=True)

    #############
    # Callbacks #
    #############

    def after_add_addon(self, user):
        password = str(uuid.uuid4())
        status = client.createuser(
            name=user.fullname,
            username=user.username,
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


class GitlabGuidFile(GuidFile):

    path = fields.StringField(index=True)

    @property
    def file_url(self):
        if self.path is None:
            raise ValueError('Path field must be defined.')
        return os.path.join('github', 'file', self.path)
