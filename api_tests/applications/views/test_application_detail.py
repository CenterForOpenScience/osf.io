import pytest
import mock

from website.models import ApiOAuth2Application, User
from website.util import api_v2_url
from tests.base import ApiTestCase
from api_tests.utils import assert_dict_contains_subset
from tests.json_api_test_app import JSONAPITestApp
from osf_tests.factories import ApiOAuth2ApplicationFactory, AuthUserFactory


def _get_application_detail_route(app):
    path = 'applications/{}/'.format(app.client_id)
    return api_v2_url(path, base_route='/')


def _get_application_list_url():
    path = 'applications/'
    return api_v2_url(path, base_route='/')

@pytest.mark.django_db
class TestApplicationDetail:

    @pytest.fixture()
    def app(self):
        return JSONAPITestApp()

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_one_app(self, user_one):
        return ApiOAuth2ApplicationFactory(owner=user_one)

    @pytest.fixture()
    def user_one_app_url(self, user_one_app):
        return _get_application_detail_route(user_one_app)

    @pytest.fixture()
    def missing_id(self):
        missing_id = {
            'data': {
                'type': 'applications',
                'attributes': {
                    'name': 'A shiny new application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io'
                }
            }
        }
        return missing_id

    @pytest.fixture()
    def missing_type(self, user_one_app):
        missing_type = {
            'data': {
                'id': user_one_app.client_id,
                'attributes': {
                    'name': 'A shiny new application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io'
                }
            }
        }
        return missing_type

    @pytest.fixture()
    def incorrect_id(self):
        incorrect_id = {
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
        return incorrect_id

    @pytest.fixture()
    def incorrect_type(self, user_one_app):
        incorrect_type = {
            'data': {
                'id': user_one_app.client_id,
                'type': 'Wrong type.',
                'attributes': {
                    'name': 'A shiny new application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io'
                }
            }
        }
        return incorrect_type

    @pytest.fixture()
    def correct(self, user_one_app):
        correct = {
            'data': {
                'id': user_one_app.client_id,
                'type': 'applications',
                'attributes': {
                    'name': 'A shiny new application',
                    'home_url': 'http://osf.io',
                    'callback_url': 'https://cos.io'
                }
            }
        }
        return correct

    def test_owner_can_view(self, app, user_one, user_one_app, user_one_app_url):
        print user_one_app_url
        res = app.get(user_one_app_url, auth=user_one.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['client_id'] == user_one_app.client_id

    def test_non_owner_cant_view(self, app, user_two, user_one_app_url):
        res = app.get(user_one_app_url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

    def test_returns_401_when_not_logged_in(self, app, user_one_app_url):
        res = app.get(user_one_app_url, expect_errors=True)
        assert res.status_code == 401

    def test_owner_can_delete(self, app, user_one, user_one_app_url):
        patcher = mock.patch('framework.auth.cas.CasClient.revoke_application_tokens', return_value=True)
        mock_method = patcher.start()
        res = app.delete(user_one_app_url, auth=user_one.auth)
        assert res.status_code == 204
        patcher.stop()

    def test_non_owner_cant_delete(self, app, user_two, user_one_app_url):
        res = app.delete(user_one_app_url,
                              auth=user_two.auth,
                              expect_errors=True)
        assert res.status_code == 403

    def test_deleting_application_makes_api_view_inaccessible(self, app, user_one, user_one_app_url):
        patcher = mock.patch('framework.auth.cas.CasClient.revoke_application_tokens', return_value=True)
        mock_method = patcher.start()
        res = app.delete(user_one_app_url, auth=user_one.auth)
        res = app.get(user_one_app_url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 404

    def test_updating_one_field_should_not_blank_others_on_patch_update(self, app, user_one, user_one_app, user_one_app_url):
        user_one_app_copy = user_one_app
        new_name = 'The instance formerly known as Prince'
        res = app.patch_json_api(user_one_app_url,
                             {'data': {'attributes':
                                  {'name': new_name},
                              'id': user_one_app.client_id,
                              'type': 'applications'
                             }}, auth=user_one.auth, expect_errors=True)
        user_one_app_copy.reload()
        assert res.status_code == 200

        assert_dict_contains_subset({'client_id': user_one_app_copy.client_id,
                                     'client_secret': user_one_app_copy.client_secret,
                                     'owner': user_one_app_copy.owner._id,
                                     'name': new_name,
                                     'description': user_one_app_copy.description,
                                     'home_url': user_one_app_copy.home_url,
                                     'callback_url': user_one_app_copy.callback_url
                                     },
                                    res.json['data']['attributes'])

    def test_updating_an_instance_does_not_change_the_number_of_instances(self, app, user_one, user_one_app, user_one_app_url):
        new_name = 'The instance formerly known as Prince'
        res = app.patch_json_api(user_one_app_url,
                                      {'data': {
                                          'attributes': {'name': new_name},
                                          'id': user_one_app.client_id,
                                          'type': 'applications'}}, auth=user_one.auth)
        assert res.status_code == 200

        list_url = _get_application_list_url()
        res = app.get(list_url, auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1

    def test_deleting_application_flags_instance_inactive(self, app, user_one, user_one_app, user_one_app_url):
        patcher = mock.patch('framework.auth.cas.CasClient.revoke_application_tokens', return_value=True)
        mock_method = patcher.start()
        res = app.delete(user_one_app_url, auth=user_one.auth)
        user_one_app.reload()
        assert not user_one_app.is_active
        patcher.stop()

    def test_update_application(self, app, user_one, user_one_app, user_one_app_url, missing_id, missing_type, incorrect_id, incorrect_type, correct):
        res = app.put_json_api(user_one_app_url, correct, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 200

    #   test_update_application_incorrect_type
        res = app.put_json_api(user_one_app_url, incorrect_type, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409

    #   test_update_application_incorrect_id
        res = app.put_json_api(user_one_app_url, incorrect_id, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409

    #   test_update_application_no_type
        res = app.put_json_api(user_one_app_url, missing_type, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400

    #   test_update_application_no_id
        res = app.put_json_api(user_one_app_url, missing_id, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400

    #   test_update_application_no_attributes
        payload = {'id': user_one_app.client_id, 'type': 'applications', 'name': 'The instance formerly known as Prince'}
        res = app.put_json_api(user_one_app_url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400

    #   test_partial_update_application_incorrect_type
        res = app.patch_json_api(user_one_app_url, incorrect_type, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409

    #   test_partial_update_application_incorrect_id
        res = app.patch_json_api(user_one_app_url, incorrect_id, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409

    #   test_partial_update_application_no_type
        res = app.patch_json_api(user_one_app_url, missing_type, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400

    #   test_partial_update_application_no_id
        res = app.patch_json_api(user_one_app_url, missing_id, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400

    #   test_partial_update_application_no_attributes
        payload = {
            'data':
                {'id': user_one_app.client_id,
                 'type': 'applications',
                 'name': 'The instance formerly known as Prince'
                 }
        }
        res = app.patch_json_api(user_one_app_url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
