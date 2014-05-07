"""
Ensure that all GitHub web hooks have a secret key for verification.
"""

import logging
from github3.models import GitHubError

from framework import StoredObject

from website.app import init_app
from website.models import Node

from website.addons.github.api import GitHub
from website.addons.github import utils
from website.addons.github import settings as github_settings


app = init_app('website.settings', set_backends=True, routes=True)
logging.basicConfig(level=logging.WARN)


def update_hook(node_settings):

    logging.warn(
        'Updating GitHub hook on node {0}'.format(
            node_settings.owner._id
        )
    )

    if not node_settings.hook_id or not node_settings.user_settings:
        return

    connection = GitHub.from_settings(node_settings.user_settings)
    repo = connection.repo(node_settings.user, node_settings.repo)
    hook = repo.hook(node_settings.hook_id)

    secret = utils.make_hook_secret()

    config = hook.config
    config['content_type'] = github_settings.HOOK_CONTENT_TYPE
    config['secret'] = secret

    hook.edit(config=config)

    node_settings.hook_secret = secret
    node_settings.save()


def update_hooks():
    for node in Node.find():
        node_settings = node.get_addon('github')
        if node_settings:
            try:
                update_hook(node_settings)
            except GitHubError as error:
                logging.exception(error)
                continue
    StoredObject._clear_caches()


if __name__ == '__main__':
    update_hooks()
