import json
import hmac
import hashlib
import unittest

import mock

from nose.tools import *

from tests.base import OsfTestCase

from website.addons.github import utils
from website.addons.github.api import GitHub
from website.addons.base.exceptions import HookError
from website.addons.github.exceptions import EmptyRepoError
from website.addons.github.model import AddonGitHubNodeSettings


def make_signature(secret, data):
    return hmac.new(secret, data, hashlib.sha1).hexdigest()

HOOK_PAYLOAD = json.dumps({
    'files': [],
    'message': 'fake commit',
})


class TestHookVerify(OsfTestCase):

    def setUp(self):
        super(TestHookVerify, self).setUp()
        self.node_settings = AddonGitHubNodeSettings(
            hook_secret='speakfriend',
        )

    def test_verify_no_secret(self):
        self.node_settings.hook_secret = None
        with assert_raises(HookError):
            utils.verify_hook_signature(self.node_settings, {}, {})

    def test_verify_valid(self):
        try:
            utils.verify_hook_signature(
                self.node_settings,
                HOOK_PAYLOAD,
                {
                    'X-Hub-Signature': make_signature(
                        self.node_settings.hook_secret,
                        HOOK_PAYLOAD,
                    )
                }
            )
        except HookError:
            assert 0

    def test_verify_invalid(self):
        with assert_raises(HookError):
            utils.verify_hook_signature(
                self.node_settings,
                HOOK_PAYLOAD,
                {'X-Hub-Signature': 'invalid'}
            )


class TestHookVerify(unittest.TestCase):
    @mock.patch('website.addons.github.api.GitHub.repo')
    def tests_none_trees_raise_empty_repo(self, mock_repo):
        mock_tree = mock.Mock()
        mock_tree.tree.return_value = None
        mock_repo.return_value = mock_tree

        with assert_raises(EmptyRepoError):
            GitHub().tree('', '', '')
