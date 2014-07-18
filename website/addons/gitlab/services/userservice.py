# -*- coding: utf-8 -*-

from website.addons.base.services.base import ServiceError
from website.addons.base.services import fileservice

from website.addons.gitlab.api import client, GitlabError
from website.addons.gitlab import settings as gitlab_settings

from website.addons.gitlab.services import utils


class UserServiceError(ServiceError):
    pass


class GitlabUserService(fileservice.BaseService):

    def create(self):
        utils.assert_provisioned(self.addon_model, False)
        user = self.addon_model.owner
        try:
            response = client.createuser(
                name=user.fullname,
                username=user._id,
                password=None,
                email=user.username,
                encrypted_password=user.password,
                skip_confirmation=True,
                projects_limit=gitlab_settings.PROJECTS_LIMIT,
            )
        except GitlabError:
            raise UserServiceError()
        self.addon_model.user_id = response['id']
        self.addon_model.username = response['username']
        self.addon_model.save()

    def edit(self, **kwargs):
        utils.assert_provisioned(self.addon_model, True)
        try:
            client.edituser(self.addon_model.user_id, **kwargs)
        except GitlabError:
            raise UserServiceError()
