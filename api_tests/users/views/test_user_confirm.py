import pytest
from unittest import mock

from api.base.settings.defaults import API_BASE
from osf_tests.factories import AuthUserFactory


@pytest.mark.django_db
class TestConfirmEmail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_with_email_verification(self, user):
        email = 'HurtsSoGood@eagles.burds.com'
        external_identity = {
            'ORCID': {
                '0002-0001-0001-0001': 'CREATE',
            }
        }
        token = user.add_unconfirmed_email(email, external_identity=external_identity)
        user.external_identity.update(external_identity)
        user.save()
        return user, token, email

    @pytest.fixture()
    def confirm_url(self, user_with_email_verification):
        user, _, _ = user_with_email_verification
        return f'/{API_BASE}users/{user._id}/confirm/'

    def test_get_not_allowed(self, app, confirm_url):
        res = app.get(confirm_url, expect_errors=True)
        assert res.status_code == 405

    def test_post_missing_fields(self, app, confirm_url, user_with_email_verification):
        user, _, _ = user_with_email_verification
        res = app.post_json_api(
            confirm_url,
            {'data': {'attributes': {}}},
            expect_errors=True,
            auth=user.auth
        )
        assert res.status_code == 400
        print(res.json['errors'])
        assert res.json['errors'] == [{'source': {'pointer': '/data/attributes/uid'}, 'detail': 'This field is required.'}, {'source': {'pointer': '/data/attributes/destination'}, 'detail': 'This field is required.'}, {'source': {'pointer': '/data/attributes/token'}, 'detail': 'This field is required.'}]

    def test_post_user_not_found(self, app, user_with_email_verification):
        user, _, _ = user_with_email_verification
        fake_user_id = 'abcd1'
        res = app.post_json_api(
            f'/{API_BASE}users/{fake_user_id}/confirm/',
            {
                'data': {
                    'attributes': {
                        'uid': fake_user_id,
                        'token': 'doesnotmatter',
                        'destination': 'doesnotmatter',
                    }
                }
            },
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'] == [{'detail': 'User not found.'}]

    def test_post_invalid_token(self, app, confirm_url, user_with_email_verification):
        user, _, _ = user_with_email_verification
        res = app.post_json_api(
            confirm_url,
            {
                'data': {
                    'attributes': {
                        'uid': user._id,
                        'token': 'badtoken',
                        'destination': 'doesnotmatter',
                    }
                }
            },
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'] == [{'detail': 'Invalid or expired token.'}]

    def test_post_provider_mismatch(self, app, confirm_url, user_with_email_verification):
        user, token, _ = user_with_email_verification
        user.external_identity = {}  # clear the valid provider
        user.save()

        res = app.post_json_api(
            confirm_url,
            {
                'data': {
                    'attributes': {
                        'uid': user._id,
                        'token': token,
                        'destination': 'doesnotmatter',
                    }
                }
            },
            expect_errors=True
        )
        assert res.status_code == 400
        assert 'provider mismatch' in res.json['errors'][0]['detail'].lower()

    @mock.patch('website.mails.send_mail')
    def test_post_success_create(self, mock_send_mail, app, confirm_url, user_with_email_verification):
        user, token, email = user_with_email_verification
        user.is_registered = False
        user.save()
        res = app.post_json_api(
            confirm_url,
            {
                'data': {
                    'attributes': {
                        'uid': user._id,
                        'token': token,
                        'destination': 'doesnotmatter',
                    }
                }
            },
            expect_errors=True
        )
        assert res.status_code == 201
        assert not mock_send_mail.called
        assert res.json == {
            'redirect_url': f'http://localhost:80/v2/users/{user._id}/confirm/&new=true',
            'meta': {
                'version': '2.0'
            }
        }
        assert res.status_code == 201

        user.reload()
        assert user.is_registered
        assert token not in user.email_verifications
        assert user.external_identity == {'ORCID': {'0002-0001-0001-0001': 'VERIFIED'}}
        assert user.emails.filter(address=email.lower()).exists()

    @mock.patch('website.mails.send_mail')
    def test_post_success_link(self, mock_send_mail, app, confirm_url, user_with_email_verification):
        user, token, email = user_with_email_verification
        user.external_identity['ORCID']['0000-0000-0000-0000'] = 'LINK'
        user.save()

        res = app.post_json_api(
            confirm_url,
            {
                'data': {
                    'attributes': {
                        'uid': user._id,
                        'token': token,
                        'destination': 'doesnotmatter'
                    }
                }
            },
            expect_errors=True
        )
        assert res.status_code == 201

        assert mock_send_mail.called

        user.reload()
        assert user.external_identity['ORCID']['0000-0000-0000-0000'] == 'VERIFIED'
