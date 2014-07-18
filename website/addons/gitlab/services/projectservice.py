# -*- coding: utf-8 -*-

from website.addons.base.services.base import ServiceError
from website.addons.base.services import fileservice

from website.addons.gitlab.api import client, GitlabError
from website.addons.gitlab.services import utils


class ProjectServiceError(ServiceError):
    pass


class GitlabProjectService(fileservice.BaseService):

    def get(self):
        utils.assert_provisioned(self.addon_model, True)
        try:
            return client.getproject(self.addon_model.project_id)
        except GitlabError:
            raise ProjectServiceError()

    def create(self, user_addon, create_id):
        utils.assert_provisioned(user_addon, True)
        utils.assert_provisioned(self.addon_model, False)
        try:
            response = client.createprojectuser(
                user_addon.user_id,
                create_id,
            )
        except GitlabError:
            raise ProjectServiceError()
        self.addon_model.creator_osf_id = user_addon.owner._id
        self.addon_model.project_id = response['id']
        self.addon_model.save()
        return response

    def ready(self):
        utils.assert_provisioned(self.addon_model, True)
        try:
            status = client.getprojectready(self.addon_model.project_id)
            if status['ready']:
                return True
        except GitlabError:
            pass
        return False

    def copy(self, user_addon, copy_id):
        utils.assert_provisioned(user_addon, True)
        utils.assert_provisioned(self.addon_model, True)
        response = client.createcopy(
            self.addon_model.project_id,
            user_addon.user_id,
            copy_id,
        )
        if response['id'] is None:
            raise ProjectServiceError()
        return response

    def add_member(self, user_addon, access_level):
        utils.assert_provisioned(user_addon, True)
        utils.assert_provisioned(self.addon_model, True)
        try:
            client.addprojectmember(
                self.addon_model.project_id,
                user_addon.user_id,
                access_level=access_level,
            )
        except GitlabError:
            raise ProjectServiceError()

    def edit_member(self, user_addon, access_level):
        utils.assert_provisioned(user_addon, True)
        utils.assert_provisioned(self.addon_model, True)
        try:
            client.editprojectmember(
                self.project_id,
                user_addon.user_id,
                access_level=access_level,
            )
        except GitlabError:
            raise ProjectServiceError()

    def delete_member(self, user_addon):
        utils.assert_provisioned(user_addon, True)
        utils.assert_provisioned(self.addon_model, True)
        try:
            client.deleteprojectmember(
                self.addon_model.project_id,
                user_addon.user_id,
            )
        except GitlabError:
            raise ProjectServiceError()
