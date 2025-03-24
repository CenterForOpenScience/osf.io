
import pytest
from django.middleware import csrf

from api.base.settings.defaults import API_BASE
from api.base.settings import CSRF_COOKIE_NAME
from osf.models import OSFUser


@pytest.mark.django_db
class TestConfirmEmail:

    @pytest.fixture()
    def user_one(self):
        user = OSFUser.create_unconfirmed(
            username='freddie@mercury.com',
            password='password',
            fullname='freddie@mercury.com',
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
                    'is_merge': False,
                }
            }
        }

    @pytest.fixture()
    def url(self):
        return f'/{API_BASE}users/confirm_email/'

    @pytest.fixture
    def csrf_token(self):
        return csrf._mask_cipher_secret(csrf._get_new_csrf_string())

    def test_confirm_email(self, app, payload, user_one, url, csrf_token):
        app.set_cookie(CSRF_COOKIE_NAME, csrf_token)
        res = app.post_json_api(url, payload, headers={'X-CSRFToken': csrf_token})
        assert res.status_code == 200
        user_one.refresh_from_db()
        assert user_one.is_confirmed

    def test_csrf_protection(self, app, payload, user_one, url):
        res = app.post_json_api(url, payload, expect_errors=True)
        assert res.status_code == 403

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
