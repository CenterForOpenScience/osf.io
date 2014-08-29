"""
Ensure that all GitHub web hooks have a secret key for verification.
"""

import logging
from github3.models import GitHubError
from modularodm import Q

import mock
from nose.tools import *
from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from framework.mongo import StoredObject

from website.app import init_app
from website.models import Node

from website.addons.github.api import GitHub
from website.addons.github import utils
from website.addons.github import settings as github_settings
from website.addons.github.model import AddonGitHubNodeSettings
from website.addons.github.exceptions import ApiError


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARN)


def update_hook(node_settings):
    """Discard the existing webhook for a GitHub node add-on and create a new
    one.

    """
    logger.warn(
        'Updating GitHub hook on node {0}'.format(
            node_settings.owner._id
        )
    )

    connection = GitHub.from_settings(node_settings.user_settings)
    repo = connection.repo(node_settings.user, node_settings.repo)
    hook = repo.hook(node_settings.hook_id)

    if hook is None:
        logger.warn('Hook {0} not found'.format(node_settings.hook_id))
        return

    secret = utils.make_hook_secret()

    config = hook.config
    config['content_type'] = github_settings.HOOK_CONTENT_TYPE
    config['secret'] = secret

    hook.edit(config=config)

    node_settings.hook_secret = secret
    node_settings.save()


def get_targets():
    """Get `AddonGitHubNodeSettings` records with authorization and a non-null
    webhook.

    """
    return AddonGitHubNodeSettings.find(
        Q('user_settings', 'ne', None) &
        Q('hook_id', 'ne', None)
    )


def main():
    targets = get_targets()
    for target in targets:
        try:
            update_hook(target)
        except (GitHubError, ApiError) as error:
            logging.exception(error)
            continue


class TestHookMigration(OsfTestCase):

    def setUp(self):
        super(TestHookMigration, self).setUp()
        self.project = ProjectFactory()
        self.project.creator.add_addon('github')
        self.user_addon = self.project.creator.get_addon('github')
        self.project.add_addon('github', None)
        self.node_addon = self.project.get_addon('github')
        self.node_addon.hook_id = 1
        self.node_addon.user_settings = self.user_addon
        self.node_addon.save()

    @mock.patch('website.addons.github.utils.make_hook_secret')
    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_update_hook(self, mock_repo, mock_make_secret):
        mock_make_secret.return_value = 'shh'
        update_hook(self.node_addon)
        self.node_addon.reload()
        assert_equal(self.node_addon.hook_secret, 'shh')

    def test_get_targets(self):
        AddonGitHubNodeSettings.remove()
        addons = [
            AddonGitHubNodeSettings(),
            AddonGitHubNodeSettings(hook_id=1),
            AddonGitHubNodeSettings(user_settings=self.user_addon),
            AddonGitHubNodeSettings(hook_id=1, user_settings=self.user_addon),
        ]
        for addon in addons:
            addon.save()
        targets = get_targets()
        assert_equal(targets.count(), 1)
        assert_equal(targets[0]._id, addons[-1]._id)


if __name__ == '__main__':
    app = init_app('website.settings', set_backends=True, routes=True)
    main()

