import mock
import pytest

from addons.forward.tests.utils import ForwardAddonTestCase
from tests.base import OsfTestCase
from website import settings
from tests.json_api_test_app import JSONAPITestApp

pytestmark = pytest.mark.django_db

class TestForward(ForwardAddonTestCase, OsfTestCase):

    django_app = JSONAPITestApp()

    def setUp(self):
        super(TestForward, self).setUp()
        self.app.authenticate(*self.user.auth)

    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    @mock.patch('osf.models.node.Node.do_check_spam')
    def test_change_url_check_spam(self, mock_check_spam):
        self.project.is_public = True
        self.project.save()
        self.django_app.put_json_api(
            '/v2/nodes/{}/addons/forward/'.format(self.project._id),
            {'data': {'attributes': {'url': 'http://possiblyspam.com'}}},
            auth=self.user.auth,
        )

        assert mock_check_spam.called
        data, _ = mock_check_spam.call_args
        author, author_email, content, request_headers = data

        assert author == self.user.fullname
        assert author_email == self.user.username
        assert content == 'http://possiblyspam.com'
