import json
import hmac
import hashlib

import nose
from nose.tools import *  # noqa

from tests.base import OsfTestCase

from addons.gitlab import utils
from addons.base.exceptions import HookError
from addons.gitlab.models import NodeSettings


def make_signature(secret, data):
    return hmac.new(secret.encode(), data.encode(), hashlib.sha1).hexdigest()

HOOK_PAYLOAD = json.dumps({
    'files': [],
    'message': 'fake commit',
})


class TestHookVerify(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.node_settings = NodeSettings(
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
