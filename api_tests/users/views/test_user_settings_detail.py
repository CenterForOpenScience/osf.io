# -*- coding: utf-8 -*-
import mock
import pytest
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
)
from website.settings import MAILCHIMP_GENERAL_LIST, OSF_HELP_LIST


@pytest.fixture()
def user_one():
    return AuthUserFactory()

@pytest.fixture()
def user_two():
    return AuthUserFactory()

@pytest.fixture()
def url(user_one):
    return '/{}users/{}/settings/'.format(API_BASE, user_one._id)


@pytest.mark.django_db
class TestUserSettingsGet:

    def test_get(self, app, user_one, user_two, url):
        # User unauthenticated
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # User accessing another user's settings
        res = app.get(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Incorrect method
        res = app.post(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 405
        assert res.content_type == 'application/vnd.api+json'

        # User authenticated
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200

        assert res.json['data']['attributes']['subscribe_osf_help_email'] is True
        assert res.json['data']['attributes']['subscribe_osf_general_email'] is False
        assert res.json['data']['attributes']['two_factor_enabled'] is False
        assert res.json['data']['attributes']['two_factor_confirmed'] is False
        assert res.json['data']['attributes']['secret'] is None
        assert res.json['data']['type'] == 'user_settings'

        # unconfirmed two_factor includes secret
        addon = user_one.add_addon('twofactor')
        res = app.get(url, auth=user_one.auth)
        assert res.json['data']['attributes']['two_factor_enabled'] is True
        assert res.json['data']['attributes']['two_factor_confirmed'] is False
        assert res.json['data']['attributes']['secret'] == addon.totp_secret_b32

@pytest.mark.django_db
class TestUserSettingsUpdateTwoFactor:

    @pytest.fixture()
    def payload(self, user_one):
        return {
            'data': {
                'type': 'user_settings',
                'id': user_one._id,
                'attributes': {}
            }
        }

    def test_user_settings_type(self, app, user_one, url, payload):
        payload['data']['type'] = 'Invalid type'
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409

    def test_update_two_factor_permissions(self, app, user_one, user_two, url, payload):
        payload['data']['attributes']['two_factor_enabled'] = False
        # Unauthenticated
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401
        # User modifying someone else's settings
        res = app.patch_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

    def test_update_two_factor_enabled(self, app, user_one, url, payload):
        # Invalid data type
        payload['data']['attributes']['two_factor_enabled'] = 'Yes'
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '"Yes" is not a valid boolean.'

        # Already disabled - nothing happens, still disabled
        payload['data']['attributes']['two_factor_enabled'] = False
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['two_factor_enabled'] is False
        assert res.json['data']['attributes']['secret'] is None
        assert res.json['data']['attributes']['two_factor_confirmed'] is False

        # Test enabling two factor
        payload['data']['attributes']['two_factor_enabled'] = True
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['two_factor_enabled'] is True
        user_one.reload()
        addon = user_one.get_addon('twofactor')
        assert addon.deleted is False
        assert addon.is_confirmed is False
        assert res.json['data']['attributes']['secret'] == addon.totp_secret_b32
        assert res.json['data']['attributes']['two_factor_confirmed'] is False

        # Test already enabled - nothing happens, still enabled
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['two_factor_enabled'] is True
        assert res.json['data']['attributes']['secret'] == addon.totp_secret_b32

        # Test disabling two factor
        payload['data']['attributes']['two_factor_enabled'] = False
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['two_factor_enabled'] is False
        assert res.json['data']['attributes']['two_factor_confirmed'] is False
        assert res.json['data']['attributes']['secret'] is None
        user_one.reload()
        addon = user_one.get_addon('twofactor')
        assert addon is None

    @mock.patch('addons.twofactor.models.UserSettings.verify_code')
    def test_update_two_factor_verification(self, mock_verify_code, app, user_one, url, payload):
        # Two factor not enabled
        mock_verify_code.return_value = True
        payload['data']['attributes']['two_factor_verification'] = 123456
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Two-factor authentication is not enabled.'

        # Two factor invalid code
        mock_verify_code.return_value = False
        payload['data']['attributes']['two_factor_enabled'] = True
        payload['data']['attributes']['two_factor_verification'] = 123456
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'The two-factor verification code you provided is invalid.'

        # Test invalid data type
        mock_verify_code.return_value = False
        payload['data']['attributes']['two_factor_verification'] = 'abcd123'
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'A valid integer is required.'

        # Test two factor valid code
        mock_verify_code.return_value = True
        del payload['data']['attributes']['two_factor_verification']
        res = app.patch_json_api(url, payload, auth=user_one.auth)
        payload['data']['attributes']['two_factor_verification'] = 654321
        res = app.patch_json_api(url, payload, auth=user_one.auth)

        assert res.json['data']['attributes']['two_factor_enabled'] is True
        assert res.json['data']['attributes']['secret'] is None
        assert res.json['data']['attributes']['two_factor_confirmed'] is True
        assert res.status_code == 200
        user_one.reload()
        addon = user_one.get_addon('twofactor')
        assert addon.deleted is False
        assert addon.is_confirmed is True


@pytest.mark.django_db
class TestUserSettingsUpdateMailingList:

    @pytest.fixture()
    def payload(self, user_one):
        return {
            'data': {
                'id': user_one._id,
                'type': 'user_settings',
                'attributes': {
                    'subscribe_osf_help_email': False,
                    'subscribe_osf_general_email': True
                }
            }
        }

    @pytest.fixture()
    def bad_payload(self, user_one):
        return {
            'data': {
                'id': user_one._id,
                'type': 'user_settings',
                'attributes': {
                    'subscribe_osf_help_email': False,
                    'subscribe_osf_general_email': '22',
                }

            }
        }

    @mock.patch('api.users.serializers.update_mailchimp_subscription')
    def test_authorized_patch_200(self, mailchimp_mock, app, user_one, payload, url):
        res = app.patch_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 200

        user_one.refresh_from_db()
        assert user_one.osf_mailing_lists[OSF_HELP_LIST] is False
        mailchimp_mock.assert_called_with(user_one, MAILCHIMP_GENERAL_LIST, True)

    def test_bad_payload_patch_400(self, app, user_one, bad_payload, url):
        res = app.patch_json_api(url, bad_payload, auth=user_one.auth, expect_errors=True)

        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == u'"22" is not a valid boolean.'

    def test_anonymous_patch_401(self, app, url, payload):
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401
        assert res.content_type == 'application/vnd.api+json'

    def test_unauthorized_patch_403(self, app, url, payload, user_two):
        res = app.patch_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.content_type == 'application/vnd.api+json'


@pytest.mark.django_db
class TestUpdateRequestedDeactivation:

    @pytest.fixture()
    def payload(self, user_one):
        return {
            'data': {
                'id': user_one._id,
                'type': 'user_settings',
                'attributes': {
                    'deactivation_requested': True
                }
            }
        }

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_patch_requested_deactivation(self, mock_mail, app, user_one, user_two, url, payload):
        # Logged out
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # Logged in, requesting deactivation for another user
        res = app.patch_json_api(url, payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Logged in, request to deactivate
        assert user_one.requested_deactivation is False
        res = app.patch_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 200
        user_one.reload()
        assert user_one.requested_deactivation is True

        # Logged in, deactivation already requested
        res = app.patch_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 200
        user_one.reload()
        assert user_one.requested_deactivation is True

        # Logged in, request to cancel deactivate request
        payload['data']['attributes']['deactivation_requested'] = False
        res = app.patch_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 200
        user_one.reload()
        assert user_one.requested_deactivation is False

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_patch_invalid_type(self, mock_mail, app, user_one, url, payload):
        assert user_one.email_last_sent is None
        payload['data']['type'] = 'Invalid Type'
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 409
        user_one.reload()
        assert user_one.email_last_sent is None
        assert mock_mail.call_count == 0

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_exceed_throttle(self, mock_mail, app, user_one, url, payload):
        assert user_one.email_last_sent is None
        res = app.patch_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 200

        res = app.patch_json_api(url, payload, auth=user_one.auth)
        assert res.status_code == 200

        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 429
