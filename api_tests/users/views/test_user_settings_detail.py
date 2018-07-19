# -*- coding: utf-8 -*-
import pytest
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
)
from addons.twofactor.tests.utils import _valid_code


@pytest.fixture()
def user_one():
    return AuthUserFactory()

@pytest.fixture()
def user_two():
    return AuthUserFactory()


@pytest.mark.django_db
class TestUserSettingsGet:

    @pytest.fixture()
    def url(self, user_one):
        return '/{}users/{}/settings/'.format(API_BASE, user_one._id)

    def test_get(self, app, user_one, user_two, url):
        # User unauthenticated
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # User accessing another user's settings
        res = app.get(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # User authenticated
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200


@pytest.mark.django_db
class TestUserSettingsUpdate:

    @pytest.fixture()
    def url(self, user_one):
        return '/{}users/{}/settings/'.format(API_BASE, user_one._id)

    @pytest.fixture()
    def payload(self, user_one):
        return {
            'data': {
                'type': 'user-settings',
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

        # Test enabling two factor
        payload['data']['attributes']['two_factor_enabled'] = True
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['two_factor_enabled'] is True
        user_one.reload()
        addon = user_one.get_addon('twofactor')
        assert addon.deleted is False
        assert addon.is_confirmed is False

        # Test already enabled - nothing happens, still enabled
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['two_factor_enabled'] is True

        # Test disabling two factor
        payload['data']['attributes']['two_factor_enabled'] = False
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['two_factor_enabled'] is False
        user_one.reload()
        addon = user_one.get_addon('twofactor')
        assert addon is None

    def test_update_two_factor_verification(self, app, user_one, url, payload):
        TOTP_SECRET = 'b8f85986068f8079aa9d'
        # Two factor not enabled
        payload['data']['attributes']['two_factor_verification'] = 123456
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Two-factor authentication is not enabled.'

        # Two factor invalid code
        payload['data']['attributes']['two_factor_enabled'] = True
        payload['data']['attributes']['two_factor_verification'] = 123456
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'The two-factor verification code you provided is invalid.'

        # Test invalid data type
        payload['data']['attributes']['two_factor_verification'] = 'abcd123'
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'A valid integer is required.'

        # Test two factor valid code
        del payload['data']['attributes']['two_factor_verification']
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        addon = user_one.get_addon('twofactor')
        addon.totp_secret = TOTP_SECRET
        addon.save()
        payload['data']['attributes']['two_factor_verification'] = _valid_code(TOTP_SECRET)
        res = app.patch_json_api(url, payload, auth=user_one.auth, expect_errors=True)
        assert res.json['data']['attributes']['two_factor_enabled'] is True
        assert res.status_code == 200
        user_one.reload()
        addon = user_one.get_addon('twofactor')
        assert addon.deleted is False
        assert addon.is_confirmed is True
