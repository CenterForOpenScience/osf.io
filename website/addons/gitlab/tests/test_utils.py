import json
import hmac
import hashlib

import nose
from nose.tools import *  # noqa

from tests.base import OsfTestCase

from website.addons.gitlab import utils
from website.addons.base.exceptions import HookError
from website.addons.gitlab.model import GitLabNodeSettings


def make_signature(secret, data):
    return hmac.new(secret, data, hashlib.sha1).hexdigest()

HOOK_PAYLOAD = json.dumps({
    'files': [],
    'message': 'fake commit',
})


class TestHookVerify(OsfTestCase):

    def setUp(self):
        super(TestHookVerify, self).setUp()
        self.node_settings = GitLabNodeSettings(
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


if __name__ == '__main__':
    nose.run()
