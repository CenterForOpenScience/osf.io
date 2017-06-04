import pytest

from nose.tools import assert_equal

from addons.forward.tests.utils import ForwardAddonTestCase
from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

class TestForwardLogs(ForwardAddonTestCase, OsfTestCase):

    def setUp(self):
        super(TestForwardLogs, self).setUp()
        self.app.authenticate(*self.user.auth)

    def test_change_url_log_added(self):
        log_count = self.project.logs.count()
        self.app.put_json(
            self.project.api_url_for('forward_config_put'),
            dict(
                url='http://how.to.bas/ic',
            ),
        )
        self.project.reload()
        assert_equal(
            self.project.logs.count(),
            log_count + 1
        )

    def test_change_timeout_log_not_added(self):
        log_count = self.project.logs.count()
        self.app.put_json(
            self.project.api_url_for('forward_config_put'),
            dict(
                url=self.node_settings.url,
            ),
        )
        self.project.reload()
        assert_equal(
            self.project.logs.count(),
            log_count
        )
