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

from website.addons.gitlab.utils import (
    setup_user, translate_permissions
)
from website.addons.gitlab import settings as gitlab_settings

from website.addons.gitlab.services import (
    fileservice, userservice, projectservice,
)


logger = logging.getLogger(__name__)


class GitlabUserSettings(AddonUserSettingsBase):

    ########
    # Data #
    ########

    # Account credentials
    user_id = fields.IntegerField()
    username = fields.StringField()

    @property
    def provisioned(self):
        return self.user_id is not None

    #############
    # Callbacks #
    #############

    def after_set_password(self, user):
        """Update GitLab password when OSF password changes.

        """
        user_service = userservice.GitlabUserService(self)
        try:
            user_service.edit(encrypted_password=user.password)
        except userservice.UserServiceError:
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
    # TODO: Should be updated when permissions change
    _migration_done = fields.BooleanField(default=False)

    @property
    def provisioned(self):
        return self.project_id is not None

    #############
    # Callbacks #
    #############

    def after_add_contributor(self, node, added):
        """Add new user to GitLab project.

        """
        user_settings = setup_user(added)
        permissions = node.get_permissions(added)
        try:
            access_level = translate_permissions(permissions)
        except ValueError as error:
            logger.exception(error)
            return
        project_service = projectservice.GitlabProjectService(self)
        try:
            project_service.add_member(
                user_settings,
                access_level=access_level,
            )
        except projectservice.ProjectServiceError:
            logger.error(
                'Could not add Gitlab user {0} on node {1}'.format(
                    added._id,
                    node._id,
                )
            )

    def after_set_permissions(self, node, user, permissions):
        """Update GitLab permissions.

        """
        if self.project_id is None:
            return
        user_settings = setup_user(user)
        access_level = translate_permissions(permissions)
        project_service = projectservice.GitlabProjectService(self)
        try:
            project_service.edit_member(
                user_settings,
                access_level=access_level,
            )
        except projectservice.ProjectServiceError:
            logger.error(
                u'Could not update GitLab permissions on user {0} on node{1}'.format(
                    user._id,
                    self.owner._id,
                )
            )

    def after_remove_contributor(self, node, removed):
        """Remove user from GitLab project.

        """
        if self.project_id is None:
            return
        user_settings = removed.get_addon('gitlab')
        project_service = projectservice.GitlabProjectService(self)
        try:
            project_service.delete_member(user_settings)
        except projectservice.ProjectServiceError:
            logger.error(
                'Could not remove user {0} from node {1}'.format(
                    removed._id,
                    self.owner._id,
                )
            )

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
        project_service = projectservice.GitlabProjectService(self)
        try:
            copy = project_service.copy(user_settings, fork._id)
        except projectservice.ProjectServiceError:
            raise AddonError(
                'Could not copy project on node {0}'.format(
                    node._id,
                )
            )

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

        project_service = projectservice.GitlabProjectService(self)

        # Copy project
        try:
            copy = project_service.copy(user_settings, registration._id)
        except projectservice.ProjectServiceError:
            raise AddonError(
                'Could not copy project on node {0}'.format(
                    node._id,
                )
            )

        clone.project_id = copy['id']

        # Grant all contributors read-only permissions
        # TODO: Patch Gitlab so this can be done with one API call
        access_level = translate_permissions(READ)
        try:
            project_service.edit_member(
                user_settings,
                access_level=access_level,
            )
        except projectservice.ProjectServiceError:
            logger.error(
                'Could not set GitLab permission for user {0} on node {1}'.format(
                    user._id,
                    node._id,
                )
            )
        for contrib in registration.contributors:
            if contrib == user:
                continue
            contrib_settings = contrib.get_or_add_addon('gitlab')
            try:
                project_service.add_member(contrib_settings, access_level)
            except projectservice.ProjectServiceError:
                logger.error(
                    'Could not add GitLab user for user {0} on node {1}'.format(
                        user._id,
                        node._id,
                    )
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
    def get_or_create(cls, node_settings, path, ref=None):
        """

        :param GitlabAddonNodeSettings node_settings:
        :param str path: Path to file
        :param str ref: Branch or SHA
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

            # If GUID doesn't exist, check whether file exists; we know the
            # file exists if it has at least one commit
            file_service = fileservice.GitlabFileService(node_settings)
            try:
                commits = file_service.list_commits(ref, path, per_page=1)
            except fileservice.ListCommitsError:
                raise AddonError('File not found')
            if not commits:
                raise AddonError('File not found')
            guid = cls(node=node, path=path)
            guid.save()

        return guid
