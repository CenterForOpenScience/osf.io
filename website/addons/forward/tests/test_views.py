from nose.tools import *

from website.addons.forward.tests.utils import ForwardAddonTestCase


class TestForwardLogs(ForwardAddonTestCase):

    def setUp(self):
        super(TestForwardLogs, self).setUp()
        self.app.authenticate(*self.user.auth)

    def test_change_url_log_added(self):
        log_count = len(self.project.logs)
        self.app.put_json(
            self.project.api_url_for('forward_config_put'),
            dict(
                url='http://how.to.bas/ic',
                redirectBool=True,
                redirectSecs=15,
            ),
        )
        self.project.reload()
        assert_equal(
            len(self.project.logs),
            log_count + 1
        )

    def test_change_timeout_log_not_added(self):
        log_count = len(self.project.logs)
        self.app.put_json(
            self.project.api_url_for('forward_config_put'),
            dict(
                url=self.node_settings.url,
                redirectBool=True,
                redirectSecs=15,
            ),
        )
        self.project.reload()
        assert_equal(
            len(self.project.logs),
            log_count
        )

