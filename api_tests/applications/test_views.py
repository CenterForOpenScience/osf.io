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

def _get_application_reset_route(app):
    path = "applications/{}/reset/".format(app.client_id)
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


class TestApplicationDetail(ApiTestCase):
    def setUp(self):
        super(TestApplicationDetail, self).setUp()

        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()

        self.user1_app = ApiOAuth2ApplicationFactory(owner=self.user1)
        self.user1_app_url = _get_application_detail_route(self.user1_app)

        self.missing_id = {
            'data': {
                'type': 'applications',
                'attributes': {
                    'name': 'A shiny new application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io'
                }
            }
        }

        self.missing_type = {
            'data': {
                'id': self.user1_app.client_id,
                'attributes': {
                    'name': 'A shiny new application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io'
                }
            }
        }

        self.incorrect_id = {
            'data': {
                'id': '12345',
                'type': 'applications',
                'attributes': {
                    'name': 'A shiny new application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io'
                }
            }
        }

        self.incorrect_type = {
            'data': {
                'id': self.user1_app.client_id,
                'type': 'Wrong type.',
                'attributes': {
                    'name': 'A shiny new application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io'
                }
            }
        }

        self.correct = {
            'data': {
                'id': self.user1_app.client_id,
                'type': 'applications',
                'attributes': {
                    'name': 'A shiny new application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io'
                }
            }
        }

    def test_owner_can_view(self):
        res = self.app.get(self.user1_app_url, auth=self.user1.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['client_id'], self.user1_app.client_id)

    def test_non_owner_cant_view(self):
        res = self.app.get(self.user1_app_url, auth=self.user2.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_returns_401_when_not_logged_in(self):
        res = self.app.get(self.user1_app_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_owner_can_delete(self, mock_method):
        mock_method.return_value(True)
        res = self.app.delete(self.user1_app_url, auth=self.user1.auth)
        assert_equal(res.status_code, 204)

    def test_non_owner_cant_delete(self):
        res = self.app.delete(self.user1_app_url,
                              auth=self.user2.auth,
                              expect_errors=True)
        assert_equal(res.status_code, 403)

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_deleting_application_makes_api_view_inaccessible(self, mock_method):
        mock_method.return_value(True)
        res = self.app.delete(self.user1_app_url, auth=self.user1.auth)
        res = self.app.get(self.user1_app_url, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_updating_one_field_should_not_blank_others_on_patch_update(self):
        user1_app = self.user1_app
        new_name = "The instance formerly known as Prince"
        res = self.app.patch_json_api(self.user1_app_url,
                             {'data': {'attributes':
                                  {'name': new_name},
                              'id': self.user1_app.client_id,
                              'type': 'applications'
                             }}, auth=self.user1.auth, expect_errors=True)
        user1_app.reload()
        assert_equal(res.status_code, 200)

        assert_dict_contains_subset({'client_id': user1_app.client_id,
                                     'client_secret': user1_app.client_secret,
                                     'owner': user1_app.owner._id,
                                     'name': new_name,
                                     'description': user1_app.description,
                                     'home_url': user1_app.home_url,
                                     'callback_url': user1_app.callback_url
                                     },
                                    res.json['data']['attributes'])

    def test_updating_an_instance_does_not_change_the_number_of_instances(self):
        new_name = "The instance formerly known as Prince"
        res = self.app.patch_json_api(self.user1_app_url,
                                      {'data': {
                                          'attributes': {"name": new_name},
                                          'id': self.user1_app.client_id,
                                          'type': 'applications'}}, auth=self.user1.auth)
        assert_equal(res.status_code, 200)

        list_url = _get_application_list_url()
        res = self.app.get(list_url, auth=self.user1.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']),
                     1)

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_deleting_application_flags_instance_inactive(self, mock_method):
        mock_method.return_value(True)
        res = self.app.delete(self.user1_app_url, auth=self.user1.auth)
        self.user1_app.reload()
        assert_false(self.user1_app.is_active)

    def test_update_application(self):
        res = self.app.put_json_api(self.user1_app_url, self.correct, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 200)

    def test_update_application_incorrect_type(self):
        res = self.app.put_json_api(self.user1_app_url, self.incorrect_type, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_update_application_incorrect_id(self):
        res = self.app.put_json_api(self.user1_app_url, self.incorrect_id, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_update_application_no_type(self):
        res = self.app.put_json_api(self.user1_app_url, self.missing_type, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_update_application_no_id(self):
        res = self.app.put_json_api(self.user1_app_url, self.missing_id, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_update_application_no_attributes(self):
        payload = {'id': self.user1_app.client_id, 'type': 'applications', 'name': 'The instance formerly known as Prince'}
        res = self.app.put_json_api(self.user1_app_url, payload, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_partial_update_application_incorrect_type(self):
        res = self.app.patch_json_api(self.user1_app_url, self.incorrect_type, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_partial_update_application_incorrect_id(self):
        res = self.app.patch_json_api(self.user1_app_url, self.incorrect_id, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_partial_update_application_no_type(self):
        res = self.app.patch_json_api(self.user1_app_url, self.missing_type, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_partial_update_application_no_id(self):
        res = self.app.patch_json_api(self.user1_app_url, self.missing_id, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_partial_update_application_no_attributes(self):
        payload = {
            'data':
                {'id': self.user1_app.client_id,
                 'type': 'applications',
                 'name': 'The instance formerly known as Prince'
                 }
        }
        res = self.app.patch_json_api(self.user1_app_url, payload, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def tearDown(self):
        super(TestApplicationDetail, self).tearDown()
        ApiOAuth2Application.remove()
        User.remove()


class TestApplicationReset(ApiTestCase):
    def setUp(self):
        super(TestApplicationReset, self).setUp()

        self.user1 = AuthUserFactory()

        self.user1_app = ApiOAuth2ApplicationFactory(owner=self.user1)
        self.user1_reset_url = _get_application_reset_route(self.user1_app)

        self.correct = {
            'data': {
                'id': self.user1_app.client_id,
                'type': 'applications',
                'attributes': {
                    'name': 'A shiny new application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io'
                }
            }
        }

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_revokes_tokens_and_resets(self, mock_method):
        mock_method.return_value(True)
        self.user1_app.reset_secret(save=True)
        mock_method.assert_called()
        self.user1_app.reload()
        assert_not_equal(old_secret, self.user1_app.client_secret)

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_does_not_save_without_save_param(self, mock_method):
        mock_method.return_value(True)
        old_secret = self.user1_app.client_secret
        self.user1_app.reset_secret()
        self.user1_app.reload()
        assert_equal(old_secret, self.user1_app.client_secret)

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_reset_url_revokes_tokens_and_resets(self, mock_method):
        mock_method.return_value(True)
        old_secret = self.user1_app.client_secret
        self.app.put_json_api(self.user1_reset_url, self.correct, auth=self.user1.auth, expect_errors=True)
        mock_method.assert_called()
        self.user1_app.reload()
        assert_not_equal(old_secret, self.user1_app.client_secret)

    @mock.patch('website.oauth.models.ApiOAuth2Application.reset_secret')
    def test_other_user_cannot_reset(self, mock_method):
        mock_method.return_value(True)
        self.user2 = AuthUserFactory()
        self.app.put_json_api(self.user1_reset_url, self.correct, auth=self.user2.auth, expect_errors=True)
        mock_method.assert_not_called()

    @mock.patch('website.oauth.models.ApiOAuth2Application.reset_secret')
    def test_unauth_user_cannot_reset(self, mock_method):
        mock_method.return_value(True)
        self.app.put_json_api(self.user1_reset_url, self.correct, auth=None, expect_errors=True)
        mock_method.assert_not_called()

    def tearDown(self):
        super(TestApplicationReset, self).tearDown()
        ApiOAuth2Application.remove()
        User.remove()
