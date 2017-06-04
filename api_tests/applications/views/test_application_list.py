import copy
import mock

from nose.tools import *  # flake8: noqa

from website.models import ApiOAuth2Application, User
from website.util import api_v2_url
from website.util import sanitize

from tests.base import ApiTestCase
from tests.factories import ApiOAuth2ApplicationFactory, AuthUserFactory


def _get_application_detail_route(app):
    path = "applications/{}/".format(app.client_id)
    return api_v2_url(path, base_route='/')


def _get_application_list_url():
    path = "applications/"
    return api_v2_url(path, base_route='/')


class TestApplicationList(ApiTestCase):
    def setUp(self):
        super(TestApplicationList, self).setUp()

        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()

        self.user1_apps = [ApiOAuth2ApplicationFactory(owner=self.user1) for i in xrange(3)]
        self.user2_apps = [ApiOAuth2ApplicationFactory(owner=self.user2) for i in xrange(2)]

        self.user1_list_url = _get_application_list_url()
        self.user2_list_url = _get_application_list_url()

        self.sample_data = {
            'data': {
                'type': 'applications',
                'attributes': {
                    'name': 'A shiny new application',
                    'description': "It's really quite shiny",
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io',
                    'owner': 'Value discarded',
                    'client_id': 'Value discarded',
                    'client_secret': 'Value discarded',
                }
            }
        }

    def test_user1_should_see_only_their_applications(self):
        res = self.app.get(self.user1_list_url, auth=self.user1.auth)
        assert_equal(len(res.json['data']),
                     len(self.user1_apps))

    def test_user2_should_see_only_their_applications(self):
        res = self.app.get(self.user2_list_url, auth=self.user2.auth)
        assert_equal(len(res.json['data']),
                     len(self.user2_apps))

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_deleting_application_should_hide_it_from_api_list(self, mock_method):
        mock_method.return_value(True)
        api_app = self.user1_apps[0]
        url = _get_application_detail_route(api_app)

        res = self.app.delete(url, auth=self.user1.auth)
        assert_equal(res.status_code, 204)

        res = self.app.get(self.user1_list_url, auth=self.user1.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']),
                     len(self.user1_apps) - 1)

    def test_created_applications_are_tied_to_request_user_with_data_specified(self):
        res = self.app.post_json_api(self.user1_list_url, self.sample_data, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 201)

        assert_equal(res.json['data']['attributes']['owner'], self.user1._id)
        # Some fields aren't writable; make sure user can't set these
        assert_not_equal(res.json['data']['attributes']['client_id'],
                         self.sample_data['data']['attributes']['client_id'])
        assert_not_equal(res.json['data']['attributes']['client_secret'],
                         self.sample_data['data']['attributes']['client_secret'])

    def test_creating_application_fails_if_callbackurl_fails_validation(self):
        data = copy.copy(self.sample_data)
        data['data']['attributes']['callback_url'] = "itunes:///invalid_url_of_doom"
        res = self.app.post_json_api(self.user1_list_url, data,
                            auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_field_content_is_sanitized_upon_submission(self):
        bad_text = "<a href='http://sanitized.name'>User_text</a>"
        cleaned_text = sanitize.strip_html(bad_text)

        payload = copy.copy(self.sample_data)
        payload['data']['attributes']['name'] = bad_text
        payload['data']['attributes']['description'] = bad_text

        res = self.app.post_json_api(self.user1_list_url, payload, auth=self.user1.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['name'], cleaned_text)

    def test_created_applications_show_up_in_api_list(self):
        res = self.app.post_json_api(self.user1_list_url, self.sample_data, auth=self.user1.auth)
        assert_equal(res.status_code, 201)

        res = self.app.get(self.user1_list_url, auth=self.user1.auth)
        assert_equal(len(res.json['data']),
                     len(self.user1_apps) + 1)

    def test_returns_401_when_not_logged_in(self):
        res = self.app.get(self.user1_list_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def tearDown(self):
        super(TestApplicationList, self).tearDown()
        ApiOAuth2Application.remove()
        User.remove()
