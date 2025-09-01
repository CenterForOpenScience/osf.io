import pytest

from api.base.settings.defaults import API_BASE
from framework.auth import Auth
from osf_tests.factories import AuthUserFactory, RetractionFactory
from osf.utils.tokens import encode


@pytest.mark.django_db
class TestSanctionResponse:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture
    def sanction(self):
        sanction = RetractionFactory()
        registration = sanction.registrations.first()
        sanction.add_authorizer(sanction.initiated_by, registration, save=True)
        return sanction

    @pytest.fixture
    def registration(self, sanction):
        return sanction.registrations.first()

    @pytest.fixture
    def url(self, sanction):
        return f'/{API_BASE}users/{sanction.initiated_by._id}/sanction_response/'

    @pytest.fixture
    def approval_token(self, sanction):
        return sanction.approval_state[sanction.initiated_by._id]['approval_token']

    @pytest.fixture()
    def sanction_url(self, user):
        return f'/{API_BASE}users/{user._id}/sanction_response/'

    @pytest.fixture()
    def token(self, user):
        return encode({'uid': user._id, 'email': user.username})

    def test_get_not_allowed(self, app, sanction_url):
        res = app.get(sanction_url, expect_errors=True)
        assert res.status_code == 405

    def test_post_missing_fields(self, app, sanction_url, user):
        res = app.post_json_api(
            sanction_url,
            {'data': {'attributes': {}}},
            auth=user.auth,
            expect_errors=True
        )
        assert res.json['errors'] == [
            {
                'source': {
                    'pointer': '/data/attributes/uid'
                },
                'detail': 'This field is required.'
            },
            {
                'source': {
                    'pointer': '/data/attributes/destination'
                },
                'detail': 'This field is required.'
            },
            {
                'source': {
                    'pointer': '/data/attributes/token'
                },
                'detail': 'This field is required.'
            },
            {
                'source': {
                    'pointer': '/data/attributes/action'
                },
                'detail': 'This field is required.'
            }
        ]
        assert res.status_code == 400

    def test_post_user_not_found(self, app, token):
        fake_uid = 'abc12'
        url = f'/{API_BASE}users/{fake_uid}/sanction_response/'
        res = app.post_json_api(
            url,
            {
                'data': {
                    'attributes': {
                        'uid': fake_uid,
                        'token': token,
                        'action': 'approve',
                        'sanction_type': 'retraction',
                        'destination': 'foo'
                    }
                }
            },
            expect_errors=True
        )
        assert res.json['errors'] == [{'detail': 'Not found.'}]

    def test_missing_action(self, app, url, sanction, registration, approval_token):
        user = sanction.initiated_by
        res = app.post_json_api(
            url,
            {
                'data': {
                    'attributes': {
                        'uid': user._id,
                        'token': approval_token,
                        'destination': 'notebook',
                        'sanction_type': 'retraction',
                    }
                }
            },
            auth=Auth(user),
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'] == [
            {
                'source': {
                    'pointer': '/data/attributes/action'
                },
                'detail': 'This field is required.'
            }
        ]

        sanction.refresh_from_db()
        registration.refresh_from_db()

    def test_post_missing_sanction_type(self, app, sanction_url, user, token):
        res = app.post_json_api(
            sanction_url,
            {
                'data': {
                    'attributes': {
                        'uid': user._id,
                        'token': token,
                        'action': 'reject',
                        'destination': 'foo'
                    }
                }
            },
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'] == [{'detail': 'sanction_type not found.'}]
