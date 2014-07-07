# -*- coding: utf-8 -*-

import os
import logging

from modularodm.exceptions import ModularOdmException

from framework.mongo import fields, Q

from website.addons.base import (
    AddonUserSettingsBase, AddonNodeSettingsBase, GuidFile,
)
from website.util.permissions import READ

from website.addons.base import AddonError

from website.addons.gitlab.api import client, GitlabError
from website.addons.gitlab.utils import (
    setup_user, translate_permissions
)
from website.addons.gitlab import settings as gitlab_settings


logger = logging.getLogger(__name__)


class GitlabUserSettings(AddonUserSettingsBase):

    ########
    # Data #
    ########

    # Account credentials
    user_id = fields.IntegerField()
    username = fields.StringField()

    #############
    # Callbacks #
    #############

    def after_set_password(self, user):
        """Update GitLab password when OSF password changes.

        """
        try:
            client.edituser(self.user_id, encrypted_password=user.password)
        except GitlabError:
            logger.error(
                'Could not set GitLab password for user {0}'.format(
                    user._id
                )
            )


class GitlabNodeSettings(AddonNodeSettingsBase):

    ########
    # Data #
    ########

    creator_osf_id = fields.StringField()
    project_id = fields.IntegerField()
    hook_id = fields.IntegerField()

    # TODO: Delete after migration
    _migration_done = fields.BooleanField(default=False)

    #############
    # Callbacks #
    #############

    def after_add_contributor(self, node, added):
        """Add new user to GitLab project.

        """
        user_settings = setup_user(added)
        permissions = node.get_permissions(added)
        access_level = translate_permissions(permissions)
        client.addprojectmember(
            self.project_id, user_settings.user_id,
            access_level=access_level
        )

    def after_set_permissions(self, node, user, permissions):
        """Update GitLab permissions.

        """
        if self.project_id is None:
            return
        user_settings = setup_user(user)
        access_level = translate_permissions(permissions)
        client.editprojectmember(
            self.project_id, user_settings.user_id,
            access_level=access_level
        )

    def after_remove_contributor(self, node, removed):
        """Remove user from GitLab project.

        """
        if self.project_id is None:
            return
        user_settings = removed.get_addon('gitlab')
        client.deleteprojectmember(self.project_id, user_settings.user_id)

    def after_fork(self, node, fork, user, save=True):
        """Copy Gitlab project as fork.

        """
        # Call superclass method
        clone, message = super(GitlabNodeSettings, self).after_fork(
            node, fork, user, save=False
        )

        # Get user settings
        user_settings = user.get_or_add_addon('gitlab')

        # Copy project
        try:
            copy = client.createcopy(
                self.project_id, user_settings.user_id, fork._id
            )
            if copy['id'] is None:
                raise AddonError('Could not copy project')
        except GitlabError:
            raise AddonError('Could not copy project')

        clone.project_id = copy['id']

        # Optionally save changes
        if save:
            clone.save()

        return clone, message

    def after_register(self, node, registration, user, save=True):
        """Copy Gitlab project as registration.

        """
        # Call superclass method
        clone, message = super(GitlabNodeSettings, self).after_register(
            node, registration, user, save=False
        )

        # Get user settings
        user_settings = user.get_or_add_addon('gitlab')

        # Copy project
        try:
            copy = client.createcopy(
                self.project_id, user_settings.user_id, registration._id
            )
            if copy['id'] is None:
                raise AddonError('Could not copy project')
        except GitlabError:
            raise AddonError('Could not copy project')

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
        return os.path.join(gitlab_settings.ROUTE, 'files', self.path)

    @classmethod
    def get_or_create(cls, node_settings, path, ref=None, client=None):
        """

        :param GitlabAddonNodeSettings node_settings:
        :param str path: Path to file
        :param str ref: Branch or SHA
        :param Gitlab client: GitLab client
        :returns: Retrieved or created GUID

        """
        node = node_settings.owner

        try:

            # If GUID has already been created, we won't redirect, and can
            # check whether the file exists below
            guid = GitlabGuidFile.find_one(
                Q('node', 'eq', node) &
                Q('path', 'eq', path)
            )

        except ModularOdmException:

            if client is None:
                return None

            # If GUID doesn't exist, check whether file exists; we know the
            # file exists if it has at least one commit
            try:
                commits = client.listrepositorycommits(
                    node_settings.project_id,
                    ref_name=ref, path=path, per_page=1
                )
            except GitlabError:
                raise AddonError('File not found')
            if not commits:
                raise AddonError('File not found')
            guid = cls(node=node, path=path)
            guid.save()

        return guid
