import pytest

from framework.auth import Auth
from osf_tests.factories import RetractionFactory
from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
class TestRetractionApprovalAPI:

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

    @pytest.fixture
    def rejection_token(self, sanction):
        return sanction.approval_state[sanction.initiated_by._id]['rejection_token']

    @pytest.mark.usefixtures('mock_gravy_valet_get_verified_links')
    def test_approve_retraction(self, app, url, sanction, registration, approval_token):
        user = sanction.initiated_by
        res = app.post_json_api(
            url,
            {
                'data': {
                    'attributes': {
                        'uid': user._id,
                        'token': approval_token,
                        'action': 'approve',
                        'destination': 'notebook',
                        'sanction_type': 'retraction',
                    }
                }
            },
            auth=Auth(user)
        )
        assert res.status_code == 201

        sanction.refresh_from_db()
        registration.refresh_from_db()

        assert sanction.is_approved
        assert sanction.approval_state[user._id]['has_approved'] is True
        assert registration.is_retracted

    def test_reject_retraction(self, app, url, sanction, rejection_token):
        user = sanction.initiated_by
        res = app.post_json_api(
            url,
            {
                'data': {
                    'attributes': {
                        'uid': user._id,
                        'token': rejection_token,
                        'action': 'reject',
                        'destination': 'notebook',
                        'sanction_type': 'retraction',
                    }
                }
            },
            auth=Auth(user)
        )
        assert res.status_code == 201

        sanction.refresh_from_db()

        assert sanction.is_rejected
        assert sanction.approval_state[user._id]['has_rejected'] is True
