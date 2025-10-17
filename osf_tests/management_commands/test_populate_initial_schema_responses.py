import pytest

from osf.management.commands.populate_initial_schema_responses import populate_initial_schema_responses
from osf.models import SchemaResponse, SchemaResponseBlock
from osf.utils.workflows import ApprovalStates, RegistrationModerationStates as RegStates
from osf_tests.factories import ProjectFactory, RegistrationFactory
from osf_tests.utils import get_default_test_schema

DEFAULT_RESPONSES = {
    'q1': 'An answer', 'q2': 'Another answer', 'q3': 'A', 'q4': ['E'], 'q5': '', 'q6': [],
}

@pytest.fixture
def control_registration():
    return RegistrationFactory()


@pytest.fixture
def test_registration():
    registration = RegistrationFactory(schema=get_default_test_schema())
    registration.schema_responses.clear()
    registration.registration_responses = dict(DEFAULT_RESPONSES)
    registration.save()
    return registration


@pytest.fixture
def nested_registration(test_registration):
    registration = RegistrationFactory(
        project=ProjectFactory(parent=test_registration.registered_from),
        parent=test_registration
    )
    registration.schema_responses.clear()
    return registration


@pytest.mark.django_db
class TestPopulateInitialSchemaResponses:

    def test_schema_response_created(self, test_registration):
        assert not test_registration.schema_responses.exists()

        count = populate_initial_schema_responses()
        assert count == 1

        assert test_registration.schema_responses.count() == 1

        schema_response = test_registration.schema_responses.get()
        assert schema_response.schema == test_registration.registration_schema
        assert schema_response.all_responses == test_registration.registration_responses

    @pytest.mark.parametrize(
        'registration_state, schema_response_state',
        [
            (RegStates.INITIAL, ApprovalStates.UNAPPROVED),
            (RegStates.PENDING, ApprovalStates.PENDING_MODERATION),
            (RegStates.ACCEPTED, ApprovalStates.APPROVED),
            (RegStates.EMBARGO, ApprovalStates.APPROVED),
            (RegStates.PENDING_EMBARGO_TERMINATION, ApprovalStates.APPROVED),
            (RegStates.PENDING_WITHDRAW_REQUEST, ApprovalStates.APPROVED),
            (RegStates.PENDING_WITHDRAW, ApprovalStates.APPROVED),
            (RegStates.WITHDRAWN, ApprovalStates.APPROVED),
            (RegStates.REVERTED, ApprovalStates.UNAPPROVED),
            (RegStates.REJECTED, ApprovalStates.PENDING_MODERATION),
        ]
    )
    def test_schema_response_state(
            self, test_registration, registration_state, schema_response_state):
        test_registration.moderation_state = registration_state.db_name
        test_registration.save()

        populate_initial_schema_responses()

        schema_response = test_registration.schema_responses.get()
        assert schema_response.state == schema_response_state

    def test_errors_from_invalid_keys_are_ignored(self, test_registration):
        test_registration.registration_responses.update({'invalid_key': 'lolol'})
        test_registration.save()

        populate_initial_schema_responses()

        schema_response = test_registration.schema_responses.get()
        assert schema_response.all_responses == DEFAULT_RESPONSES

    def test_populate_responses_is_atomic_per_registration(self, test_registration):
        invalid_registration = RegistrationFactory()
        invalid_registration.schema_responses.clear()
        invalid_registration.registered_schema.clear()

        count = populate_initial_schema_responses()
        assert count == 1

        assert test_registration.schema_responses.exists()
        assert not invalid_registration.schema_responses.exists()

    def test_dry_run(self, test_registration):
        # confirm that the delete works even if the schema_response isn't IN_PROGRESS
        test_registration.moderation_state = RegStates.ACCEPTED.db_name
        test_registration.save()
        with pytest.raises(RuntimeError):
            populate_initial_schema_responses(dry_run=True)

        assert not test_registration.schema_responses.exists()
        assert not SchemaResponse.objects.exists()
        assert not SchemaResponseBlock.objects.exists()

    def test_batch_size(self):
        for _ in range(5):
            r = RegistrationFactory()
            r.schema_responses.clear()
        assert not SchemaResponse.objects.exists()

        count = populate_initial_schema_responses(batch_size=3)
        assert count == 3

        assert SchemaResponse.objects.count() == 3

    def test_schema_response_not_created_for_registration_with_response(self, control_registration):
        control_registration_response = control_registration.schema_responses.get()

        count = populate_initial_schema_responses()
        assert count == 0

        assert control_registration.schema_responses.get() == control_registration_response

    def test_schema_response_not_created_for_nested_registration(self, nested_registration):
        count = populate_initial_schema_responses()
        assert count == 1  # parent registration
        assert not nested_registration.schema_responses.exists()
