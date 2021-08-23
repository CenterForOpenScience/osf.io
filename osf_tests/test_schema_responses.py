import pytest

from nose.tools import assert_raises
from osf.models import RegistrationSchemaBlock, SchemaResponseBlock, SchemaResponses
from osf_tests.factories import get_default_metaschema, RegistrationFactory

@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestCreateSchemaResponses():

    @pytest.fixture
    def registration(self, schema):
        return RegistrationFactory(schema=schema)

    @pytest.fixture
    def schema(self):
        return get_default_metaschema()

    def test_create_initial_responses_sets_attributes(self, registration, schema):
        responses = SchemaResponses.create_initial_responses(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )

        assert responses.parent == registration
        assert responses in registration.schema_responses.all()
        assert responses.schema == schema
        assert responses.initiator == registration.creator
        assert not responses.submitted_timestamp

    def test_create_initial_responses_assigns_response_blocks_and_source_revision(
            self, registration, schema):
        assert not SchemaResponseBlock.objects.exists()
        responses = SchemaResponses.create_initial_responses(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )
        # No previous SchemaResponseBlocks means all SchemaResponseBlocks in existence
        # were created by the create_initial_responses call
        created_response_blocks = set(SchemaResponseBlock.objects.all())

        # Confirm that the all of the created blocks have the created responses as their
        # source revision and that response_blocks has all of the created blocks
        assert created_response_blocks == set(responses.revised_response_blocks.all())
        assert created_response_blocks == set(responses.response_blocks.all())

    def test_create_initial_responses_creates_blocks_for_each_schema_question(
            self, registration, schema):
        assert not SchemaResponseBlock.objects.exists()
        SchemaResponses.create_initial_responses(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )
        # No previous SchemaResponseBlocks means all SchemaResponseBlocks in existence
        # were created by the create_initial_responses call
        created_response_blocks = SchemaResponseBlock.objects.all()

        # Confirm that exactly one block was created for each registration_response_key on the schema
        schema_input_blocks = RegistrationSchemaBlock.objects.filter(
            schema=schema, registration_response_key__isnull=False)
        assert schema_input_blocks.count() == created_response_blocks.count()
        for key in schema_input_blocks.values_list('registration_response_key', flat=True):
            assert created_response_blocks.filter(schema_key=key).exists()

    def test_cannot_create_initial_responses_twice(self, registration, schema):
        SchemaResponses.create_initial_responses(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )

        with assert_raises(AssertionError):
            SchemaResponses.create_initial_responses(
                initiator=registration.creator,
                parent=registration,
                schema=schema
            )

    def test_create_initial_responses_for_different_parent(self, registration, schema):
        first_responses = SchemaResponses.create_initial_responses(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )

        alternate_registration = RegistrationFactory(schema=schema)
        alternate_registration_responses = SchemaResponses.create_initial_responses(
            initiator=alternate_registration.creator,
            parent=alternate_registration,
            schema=schema,
        )

        # Confirm that a response block was created for each input block
        schema_input_blocks = RegistrationSchemaBlock.objects.filter(
            schema=schema, registration_response_key__isnull=False)
        assert (
            alternate_registration_responses.revised_response_blocks.count()
            == schema_input_blocks.count()
        )
        # Confirm that all of the response_blocks for these responses
        # have these responses as their source
        assert (
            set(alternate_registration_responses.revised_response_blocks.all())
            == set(alternate_registration_responses.response_blocks.all())
        )

        # There should be no overlap between the response blocks for the
        # two sets of "initial" responses
        assert not first_responses.response_blocks.all().intersection(
            alternate_registration_responses.response_blocks.all()
        ).exists()

    def test_create_from_previous_responses(self, registration, schema):
        initial_responses = SchemaResponses.create_initial_responses(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )

        revised_responses = SchemaResponses.create_from_previous_responses(
            initiator=registration.creator,
            previous_responses=initial_responses,
            justification='Leeeeerooooy Jeeeenkiiiinns'
        )

        assert revised_responses.initiator == registration.creator
        assert revised_responses.parent == registration
        assert revised_responses.schema == schema
        assert revised_responses.revision_justification == 'Leeeeerooooy Jeeeenkiiiinns'

        assert revised_responses != initial_responses
        assert not revised_responses.revised_response_blocks.exists()
        assert set(revised_responses.response_blocks.all()) == set(initial_responses.response_blocks.all())


class TestUpdateSchemaResponses():

    def test_all_responses_property(self):
        pass

    def test_revised_responses_property(self):
        pass

    def test_update_to_initial_responses_updates_response_blocks(self, initial_responses):
        pass

    def test_initial_update_to_revised_responses_creates_new_block(self, revised_responses):
        pass

    def test_update_to_previously_revised_response_updates_block(self, revised_responses):
        pass

    def test_update_multiple_responses(self, revised_responses):
        pass

    def test_revert_updated_response_deletes_block(self, revised_responses):
        pass

    def test_update_surfaced_by_all_responses_property(self, initial_responses):
        pass

    def test_update_surfaced_by_revised_response_keys_property(self, revised_responses):
        pass

    def test_reverted_update_surfaced_by_revised_response_keys_property(self, revised_responses):
        pass
