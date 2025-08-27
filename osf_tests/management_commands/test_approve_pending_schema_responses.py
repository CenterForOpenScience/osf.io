import pytest

from django.utils import timezone
from unittest import mock

from osf.management.commands.approve_pending_schema_responses import approve_pending_schema_responses
from osf.models import SchemaResponse
from osf.utils.workflows import ApprovalStates
from osf_tests.factories import RegistrationFactory
from tests.utils import capture_notifications
from website.settings import REGISTRATION_UPDATE_APPROVAL_TIME


EXCLUDED_STATES = [state for state in ApprovalStates if state is not ApprovalStates.UNAPPROVED]
AUTO_APPROVE_TIMESTAMP = timezone.now() - REGISTRATION_UPDATE_APPROVAL_TIME


@pytest.mark.django_db
class TestApprovePendingSchemaResponses:

    @pytest.fixture
    def control_response(self):
        reg = RegistrationFactory()
        initial_response = reg.schema_responses.last()
        initial_response.state = ApprovalStates.APPROVED
        initial_response.save()
        with capture_notifications():
            revision = SchemaResponse.create_from_previous_response(
                previous_response=initial_response, initiator=reg.creator
            )
        revision.state = ApprovalStates.UNAPPROVED
        revision.submitted_timestamp = AUTO_APPROVE_TIMESTAMP
        revision.save()
        return revision

    @pytest.fixture
    def test_response(self):
        reg = RegistrationFactory()
        initial_response = reg.schema_responses.last()
        initial_response.state = ApprovalStates.APPROVED
        initial_response.save()
        with capture_notifications():
            return SchemaResponse.create_from_previous_response(
                previous_response=initial_response, initiator=reg.creator
            )

    @pytest.mark.parametrize(
        'is_moderated, expected_state',
        [(False, ApprovalStates.APPROVED), (True, ApprovalStates.PENDING_MODERATION)]
    )
    def test_auto_approval(self, control_response, is_moderated, expected_state):
        with mock.patch(
            'osf.models.schema_response.SchemaResponse.is_moderated',
            new_callaoble=mock.PropertyMock
        ) as mock_is_moderated:
            mock_is_moderated.return_value = is_moderated
            count = approve_pending_schema_responses()

        assert count == 1

        control_response.refresh_from_db()
        assert control_response.state is expected_state

    def test_auto_approval_with_multiple_pending_schema_responses(
            self, control_response, test_response):
        test_response.state = ApprovalStates.UNAPPROVED
        test_response.submitted_timestamp = AUTO_APPROVE_TIMESTAMP
        test_response.save()

        count = approve_pending_schema_responses()
        assert count == 2

        control_response.refresh_from_db()
        test_response.refresh_from_db()
        assert control_response.state is ApprovalStates.APPROVED
        assert test_response.state is ApprovalStates.APPROVED

    @pytest.mark.parametrize('revision_state', EXCLUDED_STATES)
    def test_auto_approval_only_approves_unapproved_schema_responses(
            self, control_response, test_response, revision_state):
        test_response.state = revision_state
        test_response.submitted_timestamp = AUTO_APPROVE_TIMESTAMP
        test_response.save()

        count = approve_pending_schema_responses()
        assert count == 1

        control_response.refresh_from_db()
        test_response.refresh_from_db()
        assert control_response.state is ApprovalStates.APPROVED
        assert test_response.state is revision_state

    def test_auto_approval_only_approves_schema_responses_older_than_threshold(
            self, control_response, test_response):
        test_response.state = ApprovalStates.UNAPPROVED
        test_response.submitted_timestamp = timezone.now()
        test_response.save()

        count = approve_pending_schema_responses()
        assert count == 1

        control_response.refresh_from_db()
        test_response.refresh_from_db()
        assert control_response.state is ApprovalStates.APPROVED
        assert test_response.state is ApprovalStates.UNAPPROVED

    def test_auto_approval_does_not_pick_up_initial_responses(
            self, control_response, test_response):
        test_response = test_response.previous_response
        test_response.state = ApprovalStates.UNAPPROVED
        test_response.submitted_timestamp = timezone.now()
        test_response.save()

        count = approve_pending_schema_responses()
        assert count == 1

        control_response.refresh_from_db()
        test_response.refresh_from_db()
        assert control_response.state is ApprovalStates.APPROVED
        assert test_response.state is ApprovalStates.UNAPPROVED

    def test_dry_run(self, control_response):

        with pytest.raises(RuntimeError):
            approve_pending_schema_responses(dry_run=True)

        control_response.refresh_from_db()
        assert control_response.state is ApprovalStates.UNAPPROVED
