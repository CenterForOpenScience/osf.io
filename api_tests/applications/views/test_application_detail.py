import pytest
import mock

from website.util import api_v2_url
from tests.base import assert_dict_contains_subset
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
class TestApplicationDetail:

    @pytest.fixture()
    def user_app(self, user):
        return ApiOAuth2ApplicationFactory(owner=user)

    @pytest.fixture()
    def user_app_url(self, user_app):
        return _get_application_detail_route(user_app)

    @pytest.fixture()
    def make_payload(self, user_app):

        def payload(type='applications', id=user_app.client_id):
            return {
                'data': {
                    'id': id,
                    'type': type,
                    'attributes': {
                        'name': 'A shiny new application',
                        'home_url': 'http://osf.io',
                        'callback_url': 'https://cos.io'
                    }
                }
            }

        return payload

    def test_owner_can_view(self, app, user, user_app, user_app_url):
        res = app.get(user_app_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['client_id'] == user_app.client_id

    def test_non_owner_cant_view(self, app, user_app_url):
        non_owner = AuthUserFactory()
        res = app.get(user_app_url, auth=non_owner.auth, expect_errors=True)
        assert res.status_code == 403

    def test_returns_401_when_not_logged_in(self, app, user_app_url):
        res = app.get(user_app_url, expect_errors=True)
        assert res.status_code == 401

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_owner_can_delete(self, mock_method, app, user, user_app_url):
        mock_method.return_value(True)
        res = app.delete(user_app_url, auth=user.auth)
        assert res.status_code == 204

    def test_non_owner_cant_delete(self, app, user_app_url):
        non_owner = AuthUserFactory()
        res = app.delete(
            user_app_url, auth=non_owner.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_deleting_application_makes_api_view_inaccessible(
            self, mock_method, app, user, user_app_url):
        mock_method.return_value(True)
        res = app.delete(user_app_url, auth=user.auth)
        res = app.get(user_app_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_updating_one_field_should_not_blank_others_on_patch_update(
            self, app, user, user_app, user_app_url):
        user_app_copy = user_app
        new_name = 'The instance formerly known as Prince'
        res = app.patch_json_api(
            user_app_url,
            {
                'data': {
                    'attributes': {'name': new_name},
                    'id': user_app.client_id,
                    'type': 'applications'
                }
            }, auth=user.auth, expect_errors=True)
        user_app_copy.reload()
        assert res.status_code == 200

        assert_dict_contains_subset(
            {
                'client_id': user_app_copy.client_id,
                'client_secret': user_app_copy.client_secret,
                'owner': user_app_copy.owner._id,
                'name': new_name,
                'description': user_app_copy.description,
                'home_url': user_app_copy.home_url,
                'callback_url': user_app_copy.callback_url
            },
            res.json['data']['attributes']
        )

    def test_updating_an_instance_does_not_change_the_number_of_instances(
            self, app, user, user_app, user_app_url):
        new_name = 'The instance formerly known as Prince'
        res = app.patch_json_api(
            user_app_url,
            {
                'data': {
                    'attributes': {'name': new_name},
                    'id': user_app.client_id,
                    'type': 'applications'
                }
            }, auth=user.auth
        )
        assert res.status_code == 200

        list_url = _get_application_list_url()
        res = app.get(list_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1

    @mock.patch('framework.auth.cas.CasClient.revoke_application_tokens')
    def test_deleting_application_flags_instance_inactive(
            self, mock_method, app, user, user_app, user_app_url):
        mock_method.return_value(True)
        app.delete(user_app_url, auth=user.auth)
        user_app.reload()
        assert not user_app.is_active

    def test_update_application(
            self, app, user, user_app, user_app_url, make_payload):

        valid_payload = make_payload()
        incorrect_type_payload = make_payload(type='incorrect')
        incorrect_id_payload = make_payload(id='12345')
        missing_type_payload = make_payload()
        del missing_type_payload['data']['type']
        missing_id_payload = make_payload()
        del missing_id_payload['data']['id']

        res = app.put_json_api(
            user_app_url,
            valid_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 200

    #   test_update_application_incorrect_type_payload
        res = app.put_json_api(
            user_app_url,
            incorrect_type_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    #   test_update_application_incorrect_id_payload
        res = app.put_json_api(
            user_app_url,
            incorrect_id_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    #   test_update_application_no_type
        res = app.put_json_api(
            user_app_url,
            missing_type_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    #   test_update_application_no_id
        res = app.put_json_api(
            user_app_url,
            missing_id_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    #   test_update_application_no_attributes
        payload = {
            'id': user_app.client_id,
            'type': 'applications',
            'name': 'The instance formerly known as Prince'
        }
        res = app.put_json_api(
            user_app_url,
            payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    #   test_partial_update_application_incorrect_type_payload
        res = app.patch_json_api(
            user_app_url,
            incorrect_type_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    #   test_partial_update_application_incorrect_id_payload
        res = app.patch_json_api(
            user_app_url,
            incorrect_id_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 409

    #   test_partial_update_application_no_type
        res = app.patch_json_api(
            user_app_url,
            missing_type_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    #   test_partial_update_application_no_id
        res = app.patch_json_api(
            user_app_url,
            missing_id_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400

    #   test_partial_update_application_no_attributes
        payload = {
            'data': {
                'id': user_app.client_id,
                'type': 'applications',
                'name': 'The instance formerly known as Prince'
            }
        }
        res = app.patch_json_api(
            user_app_url,
            payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
