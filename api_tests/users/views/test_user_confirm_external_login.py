import pytest
from django.middleware import csrf

from api.base.settings.defaults import API_BASE
from api.base.settings import CSRF_COOKIE_NAME
from osf.models import OSFUser


@pytest.mark.django_db
class TestConfirmExternalLogin:

    @pytest.fixture()
    def user_one(self):
        external_identity = {
            'orcid': {
                '1234': 'CREATE',
            },
        }
        user = OSFUser.create_unconfirmed(
            username='freddie@mercury.com',
            password=None,
            fullname='freddie@mercury.com',
            external_identity=external_identity,
            campaign=None,
        )

        user.save()
        return user

    @pytest.fixture()
    def payload(self, user_one):
        return {
            'data': {
                'attributes': {
                    'uid': user_one._id,
                    'token': user_one.get_confirmation_token(user_one.username),
                    'destination': 'dashboard',
                }
            }
        }

    @pytest.fixture()
    def url(self):
        return f'/{API_BASE}users/external_login_comfirm_email/'

    @pytest.fixture
    def csrf_token(self):
        return csrf._mask_cipher_secret(csrf._get_new_csrf_string())

    def test_confirm_external_login(self, app, payload, user_one, url, csrf_token):
        app.set_cookie(CSRF_COOKIE_NAME, csrf_token)
        res = app.post_json_api(url, payload, headers={'X-CSRFToken': csrf_token})
        assert res.status_code == 200
        user_one.refresh_from_db()
        assert user_one.external_identity['orcid']['1234'] == 'VERIFIED'

    def test_invalid_user(self, app, payload, url, csrf_token):
        app.set_cookie(CSRF_COOKIE_NAME, csrf_token)
        payload['data']['attributes']['uid'] = 'invalid'
        res = app.post_json_api(url, payload, expect_errors=True, headers={'X-CSRFToken': csrf_token})
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'User not found.'

    def test_invalid_token(self, app, payload, user_one, url, csrf_token):
        app.set_cookie(CSRF_COOKIE_NAME, csrf_token)
        payload['data']['attributes']['token'] = 'invalid'
        res = app.post_json_api(url, payload, expect_errors=True, headers={'X-CSRFToken': csrf_token})
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid token.'

    def test_invalid_destination(self, app, payload, user_one, url, csrf_token):
        app.set_cookie(CSRF_COOKIE_NAME, csrf_token)
        del payload['data']['attributes']['destination']
        res = app.post_json_api(url, payload, expect_errors=True, headers={'X-CSRFToken': csrf_token})
        assert res.status_code == 400
