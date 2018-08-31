# -*- coding: utf-8 -*-
import mock
import pytest
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
)

@pytest.fixture()
def user_one():
    return AuthUserFactory()

@pytest.fixture()
def user_two():
    return AuthUserFactory()


@pytest.mark.django_db
class TestUserRequestExport:

    @pytest.fixture()
    def url(self, user_one):
        return '/{}users/{}/settings/export/'.format(API_BASE, user_one._id)

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'type': 'user-account-export-form',
                'attributes': {}
            }
        }

    def test_get(self, app, user_one, url):
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 405

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_post(self, mock_mail, app, user_one, user_two, url, payload):
        # Logged out
        res = app.post_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # Logged in, requesting export for another user
        res = app.post_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in
        assert user_one.email_last_sent is None
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204
        user_one.reload()
        assert user_one.email_last_sent is not None
        assert mock_mail.call_count == 1

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_post_invalid_type(self, mock_mail, app, user_one, url, payload):
        assert user_one.email_last_sent is None
        payload['data']['type'] = 'Invalid Type'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409
        user_one.reload()
        assert user_one.email_last_sent is None
        assert mock_mail.call_count == 0

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_exceed_throttle(self, mock_mail, app, user_one, url, payload):
        assert user_one.email_last_sent is None
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204

        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204

        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 429


@pytest.mark.django_db
class TestUserRequestDeactivate:

    @pytest.fixture()
    def url(self, user_one):
        return '/{}users/{}/settings/deactivate/'.format(API_BASE, user_one._id)

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'type': 'user-account-deactivate-form',
                'attributes': {}
            }
        }

    def test_get(self, app, user_one, url):
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 405

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_post(self, mock_mail, app, user_one, user_two, url, payload):
        # Logged out
        res = app.post_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # Logged in, requesting export for another user
        res = app.post_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in
        assert user_one.email_last_sent is None
        assert user_one.requested_deactivation is False
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204
        user_one.reload()
        assert user_one.email_last_sent is not None
        assert user_one.requested_deactivation is True
        assert mock_mail.call_count == 1

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_post_invalid_type(self, mock_mail, app, user_one, url, payload):
        assert user_one.email_last_sent is None
        payload['data']['type'] = 'Invalid Type'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409
        user_one.reload()
        assert user_one.email_last_sent is None
        assert mock_mail.call_count == 0

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_exceed_throttle(self, mock_mail, app, user_one, url, payload):
        assert user_one.email_last_sent is None
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204

        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204

        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 429


@pytest.mark.django_db
class TestUserChangePassword:

    @pytest.fixture()
    def user_one(self):
        user = AuthUserFactory()
        user.set_password('password1')
        user.auth = (user.username, 'password1')
        user.save()
        return user

    @pytest.fixture()
    def url(self, user_one):
        return '/{}users/{}/settings/password/'.format(API_BASE, user_one._id)

    @pytest.fixture()
    def payload(self, user_one):
        return {
            'data': {
                'type': 'user_password',
                'id': '{}'.format(user_one._id),
                'attributes': {
                    'existing_password': 'password1',
                    'new_password': 'password2',
                    'confirm_new_password': 'password2'
                }
            }
        }

    def test_get(self, app, user_one, url):
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 405

    def test_post(self, app, user_one, user_two, url, payload):
        # Logged out
        res = app.post_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # Logged in, requesting export for another user
        res = app.post_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204
        user_one.reload()
        assert user_one.check_password('password2')

    def test_post_validation_old_password_invalid(self, app, user_one, url, payload):
        payload['data']['attributes']['existing_password'] = 'bad password'
        payload['data']['attributes']['new_password'] = 'password2'
        payload['data']['attributes']['confirm_new_password'] = 'password2'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Old password is invalid'

    def test_post_validation_matching_passwords(self, app, user_one, url, payload):
        payload['data']['attributes']['existing_password'] = 'password1'
        payload['data']['attributes']['new_password'] = 'password2'
        payload['data']['attributes']['confirm_new_password'] = 'doesn\'t match'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Password does not match the confirmation'

    def test_post_validation_not_all_the_same(self, app, user_one, url, payload):
        payload['data']['attributes']['existing_password'] = 'password1'
        payload['data']['attributes']['new_password'] = 'password1'
        payload['data']['attributes']['confirm_new_password'] = 'password1'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Password cannot be the same'

    def test_post_validation_not_email(self, app, user_one, url, payload):
        payload['data']['attributes']['existing_password'] = 'password1'
        payload['data']['attributes']['new_password'] = user_one.email
        payload['data']['attributes']['confirm_new_password'] = user_one.email
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Password cannot be the same as your email address'

    def test_post_validation_not_blank(self, app, user_one, url, payload):
        payload['data']['attributes']['existing_password'] = 'password1'
        payload['data']['attributes']['new_password'] = ''
        payload['data']['attributes']['confirm_new_password'] = ''
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be blank.'

    def test_post_validation_not_too_short(self, app, user_one, url, payload):
        payload['data']['attributes']['existing_password'] = 'password1'
        payload['data']['attributes']['new_password'] = '123'
        payload['data']['attributes']['confirm_new_password'] = '123'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Password should be at least eight characters'

    def test_post_validation_not_too_long(self, app, user_one, url, payload):
        long_password = 'X' * 257
        payload['data']['attributes']['existing_password'] = 'password1'
        payload['data']['attributes']['new_password'] = long_password
        payload['data']['attributes']['confirm_new_password'] = long_password
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Password should not be longer than 256 characters'

    def test_post_invalid_type(self, app, user_one, url, payload):
        payload['data']['type'] = 'Invalid Type'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409

    def test_exceed_throttle(self, app, user_one, url, payload):
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204
        user_one.auth = (user_one.username, 'password2')

        payload['data']['attributes']['existing_password'] = 'password2'
        payload['data']['attributes']['new_password'] = 'password3'
        payload['data']['attributes']['confirm_new_password'] = 'password3'
        res = app.post_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 204
        user_one.auth = (user_one.username, 'password3')

        payload['data']['attributes']['existing_password'] = 'password3'
        payload['data']['attributes']['new_password'] = 'password3'
        payload['data']['attributes']['confirm_new_password'] = 'Doesn\'t matter should be throttled'
        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 429

    def test_exceed_throttle_failed_attempts(self, app, user_one, url, payload):
        payload['data']['attributes']['existing_password'] = 'wrong password'

        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400

        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400

        res = app.post_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 429
