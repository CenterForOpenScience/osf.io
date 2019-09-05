import mock
import pytest

from addons.forward.tests.utils import ForwardAddonTestCase
from tests.base import OsfTestCase
from website import settings
from tests.json_api_test_app import JSONAPITestApp

pytestmark = pytest.mark.django_db

class TestForward(ForwardAddonTestCase, OsfTestCase):
    """
    Forward (the redirect url has two v2 routes, one is addon based `/v2/nodes/{}/addons/forward/` one is node settings
    based `/v2/nodes/{}/settings/` they both need to be checked for spam each time they are used to modify a redirect url.
    """

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

    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    @mock.patch('osf.models.node.Node.do_check_spam')
    def test_change_url_check_spam_node_settings(self, mock_check_spam):
        self.project.is_public = True
        self.project.save()

        payload = {
            'data': {
                'type': 'node-settings',
                'attributes': {
                    'access_requests_enabled': False,
                    'redirect_link_url': 'http://possiblyspam.com',
                },
            },
        }

        self.django_app.put_json_api(
            '/v2/nodes/{}/settings/'.format(self.project._id),
            payload,
            auth=self.user.auth,
        )

        assert mock_check_spam.called
        data, _ = mock_check_spam.call_args
        author, author_email, content, request_headers = data

        assert author == self.user.fullname
        assert author_email == self.user.username
        assert content == 'http://possiblyspam.com'

    def test_invalid_url(self):
        res = self.django_app.put_json_api(
            '/v2/nodes/{}/addons/forward/'.format(self.project._id),
            {'data': {'attributes': {'url': 'bad url'}}},
            auth=self.user.auth, expect_errors=True,
        )
        assert res.status_code == 400
        error = res.json['errors'][0]

        assert error['detail'] == 'Enter a valid URL.'
