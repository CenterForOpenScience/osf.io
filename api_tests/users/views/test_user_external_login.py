import itsdangerous
import pytest
from website import settings
from api.base.settings.defaults import API_BASE
from osf.models import OSFUser
from osf_tests.factories import UserFactory
from importlib import import_module
from django.conf import settings as django_conf_settings

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore


@pytest.mark.django_db
class TestExternalLogin:

    @pytest.fixture()
    def user_one(self):
        user = UserFactory()
        user.set_password('password1')
        user.auth = (user.username, 'password1')
        user.save()
        return user

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'attributes': {
                    'email': 'freddie@mercury.com',
                    'accepted_terms_of_service': True
                }
            }
        }

    @pytest.fixture()
    def url(self):
        return f'/{API_BASE}users/external_login/'

    @pytest.fixture()
    def session_data(self):
        session = SessionStore()
        session['auth_user_external_id_provider'] = 'orcid'
        session['auth_user_external_id'] = '1234-1234-1234-1234'
        session['auth_user_fullname'] = 'external login'
        session['auth_user_external_first_login'] = True
        session.create()
        cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(session.session_key).decode()
        return cookie

    def test_external_login(self, app, payload, url, session_data):
        app.set_cookie(settings.COOKIE_NAME, str(session_data))
        res = app.post_json_api(url, payload)
        assert res.status_code == 200
        assert res.json == {'external_id_provider': 'orcid', 'auth_user_fullname': 'external login'}
        assert not OSFUser.objects.get(username='freddie@mercury.com').is_confirmed

    def test_invalid_payload(self, app, url, session_data):
        app.set_cookie(settings.COOKIE_NAME, str(session_data))
        payload = {
            'data': {
                'attributes': {
                }
            }
        }
        res = app.post_json_api(url, payload, expect_errors=True)
        assert res.status_code == 400

    def test_existing_user(self, app, payload, url, user_one, session_data):
        app.set_cookie(settings.COOKIE_NAME, str(session_data))
        payload['data']['attributes']['email'] = user_one.username
        res = app.post_json_api(url, payload)
        assert res.status_code == 200
        assert res.json == {'external_id_provider': 'orcid', 'auth_user_fullname': 'external login'}
        user_one.reload()
        assert user_one.username in user_one.unconfirmed_emails
