from nose.tools import *
from tests.base import OsfTestCase

import json
import hmac
import hashlib

from website.addons.base.exceptions import HookError

from website.addons.github.model import AddonGitHubNodeSettings
from website.addons.github import utils


def make_signature(secret, data):
    return hmac.new(secret, data, hashlib.sha1).hexdigest()

HOOK_PAYLOAD = json.dumps({
    'files': [],
    'message': 'fake commit',
})


class TestHookVerify(OsfTestCase):

    def setUp(self):
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
