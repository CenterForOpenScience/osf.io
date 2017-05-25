import pytest
import copy
import mock

from website.models import ApiOAuth2Application, User
from website.util import api_v2_url
from website.util import sanitize
from tests.base import ApiTestCase
from osf_tests.factories import ApiOAuth2ApplicationFactory, AuthUserFactory


def _get_application_detail_route(app):
    path = 'applications/{}/'.format(app.client_id)
    return api_v2_url(path, base_route='/')


def _get_application_list_url():
    path = 'applications/'
    return api_v2_url(path, base_route='/')

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.mark.django_db
@pytest.mark.usefixtures('app')
class TestApplicationList:

    @pytest.fixture()
    def user_apps(self, user):
        return [ApiOAuth2ApplicationFactory(owner=user) for i in xrange(3)]

    @pytest.fixture()
    def user_list_url(self):
        return _get_application_list_url()

    @pytest.fixture()
    def sample_data(self):
        sample_data = {
            'data': {
                'type': 'applications',
                'attributes': {
                    'name': 'A shiny new application',
                    'description': 'It\'s really quite shiny',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io',
                    'owner': 'Value discarded',
                    'client_id': 'Value discarded',
                    'client_secret': 'Value discarded',
                }
            }
        }
        return sample_data

    def test_user_should_see_only_their_applications(self, app, user, user_apps, user_list_url):
        res = app.get(user_list_url, auth=user.auth)
        assert len(res.json['data']) == len(user_apps)

    def test_other_user_should_see_only_their_applications(self, app, user_list_url):
        other_user = AuthUserFactory()
        other_user_apps = [ApiOAuth2ApplicationFactory(owner=other_user) for i in xrange(2)]
        
        res = app.get(user_list_url, auth=other_user.auth)
        assert len(res.json['data']) == len(other_user_apps)

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_deleting_application_should_hide_it_from_api_list(self, mock_method, app, user, user_apps, user_list_url):
        mock_method.return_value(True)
        api_app = user_apps[0]
        url = _get_application_detail_route(api_app)

        res = app.delete(url, auth=user.auth)
        assert res.status_code == 204

        res = app.get(user_list_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == len(user_apps) - 1

    def test_created_applications_are_tied_to_request_user_with_data_specified(self, app, user, user_list_url, sample_data):
        res = app.post_json_api(user_list_url, sample_data, auth=user.auth, expect_errors=True)
        assert res.status_code == 201

        assert res.json['data']['attributes']['owner'] == user._id
        # Some fields aren't writable; make sure user can't set these
        assert res.json['data']['attributes']['client_id'] != sample_data['data']['attributes']['client_id']
        assert res.json['data']['attributes']['client_secret'] != sample_data['data']['attributes']['client_secret']

    def test_creating_application_fails_if_callbackurl_fails_validation(self, app, user, user_list_url, sample_data):
        data = copy.copy(sample_data)
        data['data']['attributes']['callback_url'] = 'itunes:///invalid_url_of_doom'
        res = app.post_json_api(user_list_url, data,
                            auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    def test_field_content_is_sanitized_upon_submission(self, app, user, user_list_url, sample_data):
        bad_text = '<a href=\'http://sanitized.name\'>User_text</a>'
        cleaned_text = sanitize.strip_html(bad_text)

        payload = copy.copy(sample_data)
        payload['data']['attributes']['name'] = bad_text
        payload['data']['attributes']['description'] = bad_text

        res = app.post_json_api(user_list_url, payload, auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['name'] == cleaned_text

    def test_created_applications_show_up_in_api_list(self, app, user, user_apps, user_list_url, sample_data):
        res = app.post_json_api(user_list_url, sample_data, auth=user.auth)
        assert res.status_code == 201

        res = app.get(user_list_url, auth=user.auth)
        assert len(res.json['data']) == len(user_apps) + 1

    def test_returns_401_when_not_logged_in(self, app, user_list_url):
        res = app.get(user_list_url, expect_errors=True)
        assert res.status_code == 401
