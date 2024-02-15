import json
import hmac
import hashlib

import nose
from nose.tools import *  # noqa
import pytest

from tests.base import OsfTestCase

from addons.github.models import NodeSettings
from addons.github import utils
from addons.base.exceptions import HookError

pytestmark = pytest.mark.django_db

def make_signature(secret, data):
    return hmac.new(secret.encode(), data, hashlib.sha1).hexdigest()

HOOK_PAYLOAD = json.dumps({
    'files': [],
    'message': 'fake commit',
}).encode()


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
