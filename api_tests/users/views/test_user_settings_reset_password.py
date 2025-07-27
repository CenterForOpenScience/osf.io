import pytest
import urllib

from api.base.settings.defaults import API_BASE
from api.base.settings import CSRF_COOKIE_NAME
from osf.models import NotificationType
from osf_tests.factories import (
    UserFactory,
)
from django.middleware import csrf

from tests.utils import capture_notifications


class TestResetPassword:

    @pytest.fixture()
    def user_one(self):
        user = UserFactory()
        user.set_password('password1')
        user.auth = (user.username, 'password1')
        user.save()
        return user

    @pytest.fixture()
    def url(self):
        return f'/{API_BASE}users/reset_password/'

    @pytest.fixture
    def csrf_token(self):
        return csrf._mask_cipher_secret(csrf._get_new_csrf_string())

    def test_get(self, app, url, user_one):
        encoded_email = urllib.parse.quote(user_one.email)
        url = f'{url}?email={encoded_email}'
        with capture_notifications() as notification:
            res = app.get(url)
        assert len(notification) == 1
        assert notification[0]['type'] == NotificationType.Type.RESET_PASSWORD_CONFIRMATION
        assert res.status_code == 200
        user_one.reload()

    def test_get_invalid_email(self, app, url):
        url = f'{url}?email={'invalid_email'}'
        with capture_notifications() as notification:
            res = app.get(url)
        assert not notification
        assert res.status_code == 200

    def test_post(self, app, url, user_one, csrf_token):
        app.set_cookie(CSRF_COOKIE_NAME, csrf_token)
        encoded_email = urllib.parse.quote(user_one.email)
        url = f'{url}?email={encoded_email}'
        res = app.get(url)
        user_one.reload()
        payload = {
            'data': {
                'attributes': {
                    'uid': user_one._id,
                    'token': user_one.verification_key_v2['token'],
                    'password': 'password2',
                }
            }
        }

        res = app.post_json_api(url, payload, headers={'X-CSRFToken': csrf_token})
        user_one.reload()
        assert res.status_code == 200
        assert user_one.check_password('password2')

    def test_post_empty_payload(self, app, url, csrf_token):
        app.set_cookie(CSRF_COOKIE_NAME, csrf_token)
        payload = {
            'data': {
                'attributes': {
                }
            }
        }
        res = app.post_json_api(url, payload, expect_errors=True, headers={'X-CSRFToken': csrf_token})
        assert res.status_code == 400

    def test_post_invalid_token(self, app, url, user_one, csrf_token):
        app.set_cookie(CSRF_COOKIE_NAME, csrf_token)
        payload = {
            'data': {
                'attributes': {
                    'uid': user_one._id,
                    'token': 'invalid_token',
                    'password': 'password2',
                }
            }
        }
        res = app.post_json_api(url, payload, expect_errors=True, headers={'X-THROTTLE-TOKEN': 'test-token', 'X-CSRFToken': csrf_token})
        assert res.status_code == 400

    def test_post_invalid_password(self, app, url, user_one, csrf_token):
        app.set_cookie(CSRF_COOKIE_NAME, csrf_token)
        encoded_email = urllib.parse.quote(user_one.email)
        url = f'{url}?email={encoded_email}'
        res = app.get(url)
        user_one.reload()
        payload = {
            'data': {
                'attributes': {
                    'uid': user_one._id,
                    'token': user_one.verification_key_v2['token'],
                    'password': user_one.username,
                }
            }
        }

        res = app.post_json_api(url, payload, expect_errors=True, headers={'X-THROTTLE-TOKEN': 'test-token', 'X-CSRFToken': csrf_token})
        assert res.status_code == 400

    def test_throttle(self, app, url, user_one, csrf_token):
        app.set_cookie(CSRF_COOKIE_NAME, csrf_token)
        encoded_email = urllib.parse.quote(user_one.email)
        url = f'{url}?email={encoded_email}'
        res = app.get(url)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 429
        assert res.json['message'] == 'You have recently requested to change your password. Please wait a few minutes before trying again.'
