import pytest

from framework.auth import Auth
from osf.models import Registration
from osf_tests.factories import RegistrationApprovalFactory
from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
class TestRegistrationApproval:

    @pytest.fixture
    def registration(self):
        registration_approval = RegistrationApprovalFactory()
        registration = Registration.objects.get(registration_approval=registration_approval)
        assert registration_approval.is_pending_approval
        assert registration.is_pending_registration
        return registration

    @pytest.fixture
    def sanction(self, registration):
        sanction = registration.registration_approval
        sanction.add_authorizer(registration.creator, registration, save=True)
        return sanction

    @pytest.fixture
    def url(self, registration):
        return f'/{API_BASE}users/{registration.creator._id}/sanction_response/'

    @pytest.fixture
    def approval_token(self, sanction):
        return sanction.approval_state[sanction.initiated_by._id]['approval_token']

    @pytest.fixture
    def rejection_token(self, sanction):
        return sanction.approval_state[sanction.initiated_by._id]['rejection_token']

    @pytest.mark.usefixtures('mock_gravy_valet_get_verified_links')
    def test_approve(self, app, url, sanction, registration, approval_token):
        user = sanction.initiated_by
        res = app.post_json_api(
            url,
            {
                'data': {
                    'attributes': {
                        'uid': user._id,
                        'token': approval_token,
                        'action': 'approve',
                        'destination': 'tire',
                        'sanction_type': 'registration',
                    }
                }
            },
            auth=Auth(user)
        )
        assert res.status_code == 201

        sanction.refresh_from_db()
        registration.refresh_from_db()

        assert sanction.is_approved
        assert not registration.is_pending_registration
        assert sanction.approval_state[user._id]['has_approved'] is True

    def test_reject(self, app, url, sanction, registration, rejection_token):
        user = sanction.initiated_by
        res = app.post_json_api(
            url,
            {
                'data': {
                    'attributes': {
                        'uid': user._id,
                        'token': rejection_token,
                        'action': 'reject',
                        'destination': 'tire',
                        'sanction_type': 'registration',
                    }
                }
            },
            auth=Auth(user)
        )
        assert res.status_code == 201

        sanction.refresh_from_db()

        assert sanction.is_rejected
        assert sanction.approval_state[user._id]['has_rejected'] is True
