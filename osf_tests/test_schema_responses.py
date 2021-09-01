import pytest

from nose.tools import assert_raises
from osf.models import RegistrationSchemaBlock, SchemaResponseBlock, SchemaResponse
from osf_tests.factories import RegistrationFactory
from osf_tests.utils import get_default_test_schema

# See osft_tests.utils.default_test_schema for block types and valid answers
INITIAL_SCHEMA_RESPONSES = {
    'q1': 'Some answer',
    'q2': 'Some even longer answer',
    'q3': 'A',
    'q4': ['D', 'G'],
    'q5': '',
    'q6': ''
}

@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestCreateSchemaResponse():

    @pytest.fixture
    def registration(self, schema):
        return RegistrationFactory(schema=schema)

    @pytest.fixture
    def schema(self):
        return get_default_test_schema()

    def test_create_initial_response_sets_attributes(self, registration, schema):
        response = registration.schema_responses.get()

        assert response.parent == registration
        assert response in registration.schema_responses.all()
        assert response.schema == schema
        assert response.initiator == registration.creator
        assert not response.submitted_timestamp

    def test_create_initial_response_assigns_response_blocks_and_source_revision(
            self, registration, schema):
        response = registration.schema_responses.get()
        # No previous SchemaResponseBlocks means all SchemaResponseBlocks in existence
        # were created by the create_initial_response call
        created_response_blocks = set(SchemaResponseBlock.objects.all())

        # Confirm that the all of the created blocks have the created response as their
        # source revision and that response_blocks has all of the created blocks
        assert created_response_blocks == set(response.updated_response_blocks.all())
        assert created_response_blocks == set(response.response_blocks.all())

    def test_create_initial_response_creates_blocks_for_each_schema_question(
            self, registration, schema):
        # No previous SchemaResponseBlocks means all SchemaResponseBlocks in existence
        # were created by the create_initial_response call
        created_response_blocks = SchemaResponseBlock.objects.all()

        # Confirm that exactly one block was created for each registration_response_key on the schema
        schema_input_blocks = RegistrationSchemaBlock.objects.filter(
            schema=schema, registration_response_key__isnull=False)
        assert schema_input_blocks.count() == created_response_blocks.count()
        for key in schema_input_blocks.values_list('registration_response_key', flat=True):
            assert created_response_blocks.filter(schema_key=key).exists()

    def test_cannot_create_initial_response_twice(self, registration, schema):
        with assert_raises(AssertionError):
            SchemaResponse.create_initial_response(
                initiator=registration.creator,
                parent=registration,
                schema=schema
            )

    def test_create_initial_response_for_different_parent(self, registration, schema):
        first_response = registration.schema_responses.get()

        alternate_registration = RegistrationFactory(schema=schema)
        alternate_registration_response = alternate_registration.schema_responses.get()

        # Confirm that a response block was created for each input block
        schema_input_blocks = RegistrationSchemaBlock.objects.filter(
            schema=schema, registration_response_key__isnull=False)
        assert (
            alternate_registration_response.updated_response_blocks.count()
            == schema_input_blocks.count()
        )
        # Confirm that all of the response_blocks for these response
        # have these response as their source
        assert (
            set(alternate_registration_response.updated_response_blocks.all())
            == set(alternate_registration_response.response_blocks.all())
        )

        # There should be no overlap between the response blocks for the
        # two sets of "initial" response
        assert not first_response.response_blocks.all().intersection(
            alternate_registration_response.response_blocks.all()
        ).exists()

    def test_create_from_previous_response(self, registration, schema):
        initial_response = registration.schema_responses.get()

        revised_response = SchemaResponse.create_from_previous_response(
            initiator=registration.creator,
            previous_response=initial_response,
            justification='Leeeeerooooy Jeeeenkiiiinns'
        )

        assert revised_response.initiator == registration.creator
        assert revised_response.parent == registration
        assert revised_response.schema == schema
        assert revised_response.revision_justification == 'Leeeeerooooy Jeeeenkiiiinns'

        assert revised_response != initial_response
        assert not revised_response.updated_response_blocks.exists()
        assert set(revised_response.response_blocks.all()) == set(initial_response.response_blocks.all())


@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestUpdateSchemaResponses():

    @pytest.fixture
    def schema(self):
        return get_default_test_schema()

    @pytest.fixture
    def registration(self, schema):
        return RegistrationFactory(schema=schema)

    @pytest.fixture
    def initial_response(self, schema, registration):
        response = registration.schema_responses.get()
        response.update_responses(INITIAL_SCHEMA_RESPONSES)
        return response

    @pytest.fixture
    def revised_response(self, initial_response):
        return SchemaResponse.create_from_previous_response(
            initiator=initial_response.initiator,
            previous_response=initial_response,
            justification='Leeeeerooooy Jeeeenkiiiinns'
        )

    def test_all_responses_property(self, initial_response):
        assert initial_response.all_responses == INITIAL_SCHEMA_RESPONSES
        for block in initial_response.response_blocks.all():
            assert initial_response.all_responses[block.schema_key] == block.response

    def test_uodated_response_keys_property(self, initial_response, revised_response, schema):
        # initial_response "updates" all keys
        all_keys = set(
            RegistrationSchemaBlock.objects.filter(
                schema=schema, registration_response_key__isnull=False
            ).values_list('registration_response_key', flat=True)
        )

        assert initial_response.updated_response_keys == all_keys

        # No updated_responses on the standard revised_response
        assert not revised_response.updated_response_keys
        # Key shows up after update
        revised_response.update_responses({'q1': 'I has a new  answer'})
        assert revised_response.updated_response_keys == {'q1'}

    def test_update_responses(self, initial_response):
        assert initial_response.all_responses == INITIAL_SCHEMA_RESPONSES

        updated_responses = {
            'q1': 'Hello there',
            'q2': 'This is a new response',
            'q3': 'B',
            'q4': ['E'],
            'q5': [initial_response.initiator.id],
            'q6': 'SomeFile',
        }
        initial_response.update_responses(updated_responses)

        initial_response.refresh_from_db()
        assert initial_response.all_responses == updated_responses
        for block in initial_response.response_blocks.all():
            assert block.response == updated_responses[block.schema_key]

    def test_update_to_initial_response_updates_response_blocks_in_place(self, initial_response):
        # Call set to force evaluation
        initial_block_ids = set(initial_response.response_blocks.values_list('id', flat=True))

        initial_response.update_responses(
            {
                'q1': 'Hello there',
                'q2': 'This is a new response',
                'q3': 'B',
                'q4': ['E'],
                'q5': [initial_response.initiator.id],
                'q6': 'SomeFile'
            }
        )
        initial_response.refresh_from_db()
        updated_block_ids = set(initial_response.response_blocks.values_list('id', flat=True))
        assert initial_block_ids == updated_block_ids

    def test_initial_update_to_revised_response_creates_new_block(self, revised_response):
        q1_block = revised_response.response_blocks.get(schema_key='q1')
        other_blocks = set(revised_response.response_blocks.exclude(schema_key='q1'))

        revised_response.update_responses({'q1': 'Heeyo'})
        revised_response.refresh_from_db()

        updated_q1_block = revised_response.response_blocks.get(schema_key='q1')
        # Block for q1 should be a brand new block
        assert q1_block.id != updated_q1_block.id
        assert updated_q1_block.response == 'Heeyo'
        # All other blocks should be the same
        assert other_blocks == set(revised_response.response_blocks.exclude(schema_key='q1'))

    def test_update_to_previously_revised_response_updates_block(self, revised_response):
        revised_response.update_responses({'q1': 'Heeyo'})
        revised_response.refresh_from_db()
        updated_block = revised_response.response_blocks.get(schema_key='q1')

        revised_response.update_responses({'q1': 'Jokes!'})
        revised_response.refresh_from_db()
        assert revised_response.response_blocks.get(schema_key='q1').id == updated_block.id
        updated_block.refresh_from_db()
        assert updated_block.response == 'Jokes!'

    def test_update_without_change_is_noop(self, revised_response):
        original_block_ids = set(revised_response.response_blocks.values_list('id', flat=True))
        revised_response.update_responses(INITIAL_SCHEMA_RESPONSES)

        revised_response.refresh_from_db()
        updated_block_ids = set(revised_response.response_blocks.values_list('id', flat=True))
        assert updated_block_ids == original_block_ids
        assert not revised_response.updated_response_keys

    def test_revert_updated_response(self, revised_response):
        original_block = revised_response.response_blocks.get(schema_key='q1')
        revised_response.update_responses({'q1': 'whoops'})

        revised_response.refresh_from_db()
        updated_block = revised_response.response_blocks.get(schema_key='q1')

        revised_response.update_responses({'q1': INITIAL_SCHEMA_RESPONSES['q1']})
        revised_response.refresh_from_db()

        assert revised_response.response_blocks.get(schema_key='q1') == original_block
        assert not SchemaResponseBlock.objects.filter(id=updated_block.id).exists()
        assert 'q1' not in revised_response.updated_response_keys

    def test_update_with_mixed_modalities(self, revised_response):
        original_q2_block = revised_response.response_blocks.get(schema_key='q2')
        original_q3_block = revised_response.response_blocks.get(schema_key='q3')
        original_q4_block = revised_response.response_blocks.get(schema_key='q4')

        revised_response.update_responses({'q1': 'Heeyo', 'q4': ['D', 'E', 'F', 'G']})
        revised_response.refresh_from_db()
        updated_q1_block = revised_response.response_blocks.get(schema_key='q1')

        updated_responses = {
            'q1': 'Hello there',
            'q2': 'This is a new response',
            'q3': INITIAL_SCHEMA_RESPONSES['q3'],
            'q4': INITIAL_SCHEMA_RESPONSES['q4']
        }
        revised_response.update_responses(updated_responses)
        revised_response.refresh_from_db()

        assert revised_response.response_blocks.get(schema_key='q1').id == updated_q1_block.id
        assert revised_response.response_blocks.get(schema_key='q2').id != original_q2_block.id
        assert revised_response.response_blocks.get(schema_key='q3').id == original_q3_block.id
        assert revised_response.response_blocks.get(schema_key='q4').id == original_q4_block.id

    def test_update_with_unsupported_key_raises(self, initial_response):
        with assert_raises(ValueError):
            initial_response.update_responses({'q7': 'sneaky'})

    @pytest.mark.parametrize(
        'updated_responses',
        [
            {'q1': 'New Answer', 'q2': 'Another one', 'q7': 'Wrong key at end'},
            {'q7': 'Wrong key first', 'q1': 'New Answer', 'q2': 'Another one'},
            {'q1': 'New Answer', 'q7': 'Wrong key in the middle', 'q2': 'Another one'}
        ]
    )
    def test_update_with_unsupported_key_and_supported_keys_writes_and_raises(
            self, updated_responses, initial_response):
        with assert_raises(ValueError):
            initial_response.update_responses(updated_responses)

        initial_response.refresh_from_db()
        assert initial_response.all_responses['q1'] == updated_responses['q1']
        assert initial_response.all_responses['q2'] == updated_responses['q2']
