import pytest

from osf.models import SchemaResponses
from osf.utils.workflows import ApprovalStates
from osf_tests.factories import AuthUserFactory, RegistrationFactory


@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestSchemaResponsesApprovalFlows():

    @pytest.fixture
    def registration(self):
        return RegistrationFactory()

    @pytest.fixture
    def schema_responses(self, registration):
        schema = registration.registered_schema.first()
        return SchemaResponses.objects.create(
            parent=registration,
            schema=schema,
            initiator=registration.creator
        )

    @pytest.fixture
    def alternate_user(self):
        return AuthUserFactory()

    def test_submit_responses(self, schema_responses, alternate_user):
        assert schema_responses.state is ApprovalStates.IN_PROGRESS
        schema_responses.submit(
            user=schema_responses.initiator,
            required_approvers=[schema_responses.initiator, alternate_user]
        )

        schema_responses.refresh_from_db()
        assert schema_responses.state is ApprovalStates.UNAPPROVED
        for user in [schema_responses.initiator, alternate_user]:
            assert schema_responses.pending_approvers.filter(id=user.id).exists()

    def test_approve_responses(self, schema_responses, alternate_user):
        schema_responses.submit(
            user=schema_responses.initiator,
            required_approvers=[schema_responses.initiator, alternate_user],
        )

        schema_responses.approve(user=schema_responses.initiator)
        schema_responses.refresh_from_db()
        assert schema_responses.state is ApprovalStates.UNAPPROVED

        schema_responses.approve(user=alternate_user)
        schema_responses.refresh_from_db()
        assert schema_responses.state is ApprovalStates.APPROVED

    def test_reject_responses(self, schema_responses, alternate_user):
        schema_responses.submit(
            user=schema_responses.initiator,
            required_approvers=[schema_responses.initiator, alternate_user],
        )

        schema_responses.reject(user=schema_responses.initiator)

        schema_responses.refresh_from_db()
        assert schema_responses.state is ApprovalStates.IN_PROGRESS
        assert not schema_responses.pending_approvers.exists()
