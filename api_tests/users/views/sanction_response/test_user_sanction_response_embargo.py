import pytest

from framework.auth import Auth
from osf_tests.factories import EmbargoFactory
from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
class TestEmbargoApproval:

    @pytest.fixture
    def embargo(self):
        embargo = EmbargoFactory()
        registration = embargo.registrations.first()
        embargo.add_authorizer(embargo.initiated_by, registration, save=True)
        return embargo

    @pytest.fixture
    def registration(self, embargo):
        return embargo.registrations.first()

    @pytest.fixture
    def url(self, embargo):
        return f'/{API_BASE}users/{embargo.initiated_by._id}/sanction_response/'

    @pytest.fixture
    def approval_token(self, embargo):
        return embargo.approval_state[embargo.initiated_by._id]['approval_token']

    @pytest.fixture
    def rejection_token(self, embargo):
        return embargo.approval_state[embargo.initiated_by._id]['rejection_token']

    def test_approve_embargo(self, app, url, embargo, registration, approval_token):
        user = embargo.initiated_by
        res = app.post_json_api(
            url,
            {
                'data': {
                    'attributes': {
                        'uid': user._id,
                        'token': approval_token,
                        'action': 'approve',
                        'destination': 'tire',
                        'sanction_type': 'embargo',
                    }
                }
            },
            auth=Auth(user)
        )
        assert res.status_code == 200

        embargo.refresh_from_db()
        registration.refresh_from_db()

        assert embargo.is_approved
        assert embargo.approval_state[user._id]['has_approved'] is True
        assert registration.is_embargoed
        assert registration.embargo_end_date == embargo.embargo_end_date

    def test_reject_embargo(self, app, url, embargo, registration, rejection_token):
        user = embargo.initiated_by
        res = app.post_json_api(
            url,
            {
                'data': {
                    'attributes': {
                        'uid': user._id,
                        'token': rejection_token,
                        'action': 'reject',
                        'destination': 'tire',
                        'sanction_type': 'embargo',
                    }
                }
            },
            auth=Auth(user)
        )
        assert res.status_code == 200

        embargo.refresh_from_db()
        registration.refresh_from_db()

        assert embargo.is_rejected
        assert embargo.approval_state[user._id]['has_rejected'] is True
        assert registration.registered_from is None or registration.is_deleted
