import pytest

from framework.auth import Auth
from osf_tests.factories import EmbargoTerminationApprovalFactory
from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
class TestEmbargoTerminationApproval:

    @pytest.fixture
    def sanction(self):
        sanction = EmbargoTerminationApprovalFactory()
        registration = sanction.embargoed_registration
        sanction.add_authorizer(sanction.initiated_by, registration, save=True)
        return sanction

    @pytest.fixture
    def registration(self, sanction):
        return sanction.embargoed_registration

    @pytest.fixture
    def url(self, sanction):
        return f'/{API_BASE}users/{sanction.initiated_by._id}/sanction_response/'

    @pytest.fixture
    def approval_token(self, sanction):
        return sanction.approval_state[sanction.initiated_by._id]['approval_token']

    @pytest.fixture
    def rejection_token(self, sanction):
        return sanction.approval_state[sanction.initiated_by._id]['rejection_token']

    def test_approve_embargo_termination(self, app, url, sanction, registration, approval_token):
        assert registration.embargo_termination_approval
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
                        'sanction_type': 'embargo_termination_approval',
                    }
                }
            },
            auth=Auth(user)
        )
        assert res.status_code == 201
        registration.refresh_from_db()
        assert registration.embargo.state == 'approved'  # embargo still active because it needs unanimous approval

        res = app.post_json_api(
            f'/{API_BASE}users/{registration.creator._id}/sanction_response/',
            {
                'data': {
                    'attributes': {
                        'uid': registration.creator._id,
                        'token': sanction.approval_state[registration.creator._id]['approval_token'],
                        'action': 'approve',
                        'destination': 'tire',
                        'sanction_type': 'embargo_termination_approval',
                    }
                }
            },
            auth=Auth(registration.creator)
        )
        assert res.status_code == 201
        registration.refresh_from_db()
        assert registration.embargo.state == 'completed'  # now all agree to terminate

    def test_reject_embargo_termination(self, app, url, sanction, registration, rejection_token):
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
                        'sanction_type': 'embargo_termination_approval',
                    }
                }
            },
            auth=Auth(user)
        )
        assert res.status_code == 201

        sanction.refresh_from_db()

        assert sanction.state == 'rejected'
        assert registration.embargo.state == 'approved'  # embargo still active because it needs unanimous approval
