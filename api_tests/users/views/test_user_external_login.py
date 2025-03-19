import pytest
from api.base.settings.defaults import API_BASE
from osf.models import OSFUser
from osf_tests.factories import UserFactory


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
                    'auth_user_external_first_login': True,
                    'auth_user_fullname': 'external login',
                    'accepted_terms_of_service': True,
                    'auth_user_external_id_provider': 'orcid',
                    'auth_user_external_id': '1234-1234-1234-1234'
                }
            }
        }

    @pytest.fixture()
    def url(self):
        return f'/{API_BASE}users/external_login/'

    def test_external_login(self, app, payload, url):
        res = app.post_json_api(url, payload)
        assert res.status_code == 200
        assert res.json == {'external_id_provider': 'orcid', 'auth_user_fullname': 'external login'}
        assert not OSFUser.objects.get(username='freddie@mercury.com').is_confirmed

    def test_invalid_payload(self, app, url):
        payload = {
            'data': {
                'attributes': {
                }
            }
        }
        res = app.post_json_api(url, payload, expect_errors=True)
        assert res.status_code == 400

    def test_existing_user(self, app, payload, url, user_one):
        payload['data']['attributes']['email'] = user_one.username
        res = app.post_json_api(url, payload)
        assert res.status_code == 200
        assert res.json == {'external_id_provider': 'orcid', 'auth_user_fullname': 'external login'}
        user_one.reload()
        assert user_one.username in user_one.unconfirmed_emails
