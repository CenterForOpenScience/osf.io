import pytest

from osf.management.commands.fix_initial_schema_responses import fix_initial_schema_responses
from osf.models import SchemaResponse
from osf.utils.workflows import ApprovalStates
from osf_tests.factories import ProjectFactory, RegistrationFactory
from osf_tests.utils import get_default_test_schema

FILE_INPUT_KEY = 'q6'  # File input key from DEFAULT_TEST_SCHEMA


@pytest.fixture
def registration():
    registration = RegistrationFactory(schema=get_default_test_schema())
    registration.registration_responses[FILE_INPUT_KEY] = ['some', 'updated', 'file', 'metadata']
    registration.save()
    return registration

@pytest.fixture
def schema_response(registration):
    return registration.schema_responses.last()


@pytest.mark.django_db
class TestFixEarlySchemaResponses:

    @pytest.mark.parametrize('schema_response_state', ApprovalStates)
    def test_fix_initial_schema_responses_updates_file_input_responses(
            self, registration, schema_response, schema_response_state):
        assert schema_response.all_responses != registration.registration_responses
        schema_response.state = schema_response_state
        schema_response.save()

        fixed_count, _ = fix_initial_schema_responses()
        assert fixed_count == 1

        schema_response_file_value = schema_response.all_responses[FILE_INPUT_KEY]
        registration_file_value = registration.registration_responses[FILE_INPUT_KEY]
        assert schema_response_file_value == registration_file_value

    def test_fix_initial_schema_responses_does_not_update_non_file_keys(
            self, registration, schema_response):
        registration.registration_responses['q1'] = 'red herring'
        registration.registration_responses[FILE_INPUT_KEY] = ''
        registration.save()

        fix_initial_schema_responses()

        assert schema_response.all_responses['q1'] != registration.registration_responses['q1']

    def test_updated_responses_inherit_fixes(self, registration, schema_response):
        schema_response.state = ApprovalStates.APPROVED
        schema_response.save()
        updated_response = SchemaResponse.create_from_previous_response(
            previous_response=schema_response, initiator=schema_response.initiator
        )

        fixed_count, _ = fix_initial_schema_responses()
        assert fixed_count == 1  # only initial response actively updated

        # Update that modified other values inherits the change
        original_response_file_value = schema_response.all_responses[FILE_INPUT_KEY]
        updated_response_file_value = updated_response.all_responses[FILE_INPUT_KEY]
        assert updated_response_file_value == original_response_file_value

    def test_fix_initial_schema_responsesdoes_not_overwrite_updated_values(
            self, registration, schema_response):
        schema_response.state = ApprovalStates.APPROVED
        schema_response.save()
        updated_response = SchemaResponse.create_from_previous_response(
            previous_response=schema_response, initiator=schema_response.initiator
        )
        updated_response.update_responses({FILE_INPUT_KEY: ['intentionall', 'updated', 'value']})

        fixed_count, _ = fix_initial_schema_responses()
        assert fixed_count == 1  # initial response

        # Update that modified the file value keeps its value
        original_response_file_value = schema_response.all_responses[FILE_INPUT_KEY]
        updated_response_file_value = updated_response.all_responses[FILE_INPUT_KEY]
        assert updated_response_file_value != original_response_file_value

    def test_fix_early_schemas_deletes_non_root_schema_responses(self, registration):
        nested_registration = RegistrationFactory(
            project=ProjectFactory(parent=registration.registered_from),
            parent=registration
        )

        initial_response = SchemaResponse.create_initial_response(
            parent=nested_registration, initiator=nested_registration.creator
        )
        initial_response.state = ApprovalStates.APPROVED
        initial_response.save()
        # Create an "updated" response to test cascading delete
        updated_response = SchemaResponse.create_from_previous_response(
            previous_response=initial_response, initiator=initial_response.initiator
        )
        updated_response.sate = ApprovalStates.APPROVED
        updated_response.save()

        _, deleted_count = fix_initial_schema_responses()
        assert deleted_count == 2

        assert not nested_registration.schema_responses.exists()
