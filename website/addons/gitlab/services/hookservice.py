# -*- coding: utf-8 -*-

import urlparse

from website.addons.base.services import hookservice

from website.addons.gitlab import settings as gitlab_settings
from website.addons.gitlab.api import client, GitlabError


def get_hook_url(node_addon):
    relative_url = node_addon.owner.api_url_for('gitlab_hook_callback')
    return urlparse.urljoin(gitlab_settings.HOOK_DOMAIN, relative_url)


class GitlabHookService(hookservice.HookService):

    def create(self, save=False):
        if self.addon_model.hook_id is not None:
            raise hookservice.HookExistsError()
        try:
            status = client.addprojecthook(
                self.addon_model.project_id,
                get_hook_url(self.addon_model),
            )
            self.addon_model.hook_id = status['id']
            if save:
                self.addon_model.save()
        except GitlabError:
            raise hookservice.HookServiceError()

    def delete(self, save=False):
        if self.addon_model.hook_id is None:
            raise hookservice.NoHookError()
        try:
            client.deleteprojecthook(
                self.addon_model.project_id,
                self.addon_model.hook_id,
            )
            self.addon_model.hook_id = None
            if save:
                self.addon_model.save()
        except GitlabError:
            raise hookservice.HookServiceError()
