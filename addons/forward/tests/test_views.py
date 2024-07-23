from unittest import mock
import pytest

from addons.forward.tests.utils import ForwardAddonTestCase
from tests.base import OsfTestCase
from website import settings

pytestmark = pytest.mark.django_db

class TestForward(ForwardAddonTestCase, OsfTestCase):

    def setUp(self):
        super().setUp()

    def test_change_url_log_added(self):
        log_count = self.project.logs.count()
        self.app.put(
            self.project.api_url_for('forward_config_put'),
            json=dict(
                url='http://how.to.bas/ic',
            ),
            auth=self.user.auth
        )
        self.project.reload()
        assert self.project.logs.count() == log_count + 1

    def test_change_timeout_log_not_added(self):
        log_count = self.project.logs.count()
        self.app.put(
            self.project.api_url_for('forward_config_put'),
            json=dict(
                url=self.node_settings.url,
            ),
            auth=self.user.auth
        )
        self.project.reload()
        assert self.project.logs.count() == log_count

    @mock.patch.object(settings, 'SPAM_SERVICES_ENABLED', True)
    @mock.patch('osf.models.node.Node.do_check_spam')
    def test_change_url_check_spam(self, mock_check_spam):
        self.project.is_public = True
        self.project.save()
        self.app.put(
            self.project.api_url_for('forward_config_put'),
            json={'url': 'http://possiblyspam.com'},
            auth=self.user.auth
        )

        assert mock_check_spam.called
        data, _ = mock_check_spam.call_args
        author, author_email, content, request_headers = data

        assert author == self.user.fullname
        assert author_email == self.user.username
        assert content == 'http://possiblyspam.com'

