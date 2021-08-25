import pytest

from nose.tools import assert_raises
from osf.models import RegistrationSchemaBlock, SchemaResponseBlock, SchemaResponse
from osf_tests.factories import RegistrationFactory
from osf_tests.utils import get_default_test_schema


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
        response = SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )

        assert response.parent == registration
        assert response in registration.schema_responses.all()
        assert response.schema == schema
        assert response.initiator == registration.creator
        assert not response.submitted_timestamp

    def test_create_initial_response_assigns_response_blocks_and_source_revision(
            self, registration, schema):
        assert not SchemaResponseBlock.objects.exists()
        response = SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )
        # No previous SchemaResponseBlocks means all SchemaResponseBlocks in existence
        # were created by the create_initial_response call
        created_response_blocks = set(SchemaResponseBlock.objects.all())

        # Confirm that the all of the created blocks have the created response as their
        # source revision and that response_blocks has all of the created blocks
        assert created_response_blocks == set(response.updated_response_blocks.all())
        assert created_response_blocks == set(response.response_blocks.all())

    def test_create_initial_response_creates_blocks_for_each_schema_question(
            self, registration, schema):
        assert not SchemaResponseBlock.objects.exists()
        SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )
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
        SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )

        with assert_raises(AssertionError):
            SchemaResponse.create_initial_response(
                initiator=registration.creator,
                parent=registration,
                schema=schema
            )

    def test_create_initial_response_for_different_parent(self, registration, schema):
        first_response = SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )

        alternate_registration = RegistrationFactory(schema=schema)
        alternate_registration_response = SchemaResponse.create_initial_response(
            initiator=alternate_registration.creator,
            parent=alternate_registration,
            schema=schema,
        )

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
        initial_response = SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )

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
        return SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )

    @pytest.fixture
    def revised_response(self, initial_response):
        return SchemaResponse.create_from_previous_response(
            initiator=initial_response.initiator,
            previous_response=initial_response,
            justification='Leeeeerooooy Jeeeenkiiiinns'
        )

    def test_all_response_property(self):
        pass

    def test_revised_response_property(self):
        pass

    def test_update_to_initial_response_updates_response_blocks(self, initial_response):
        pass

    def test_initial_update_to_revised_response_creates_new_block(self, revised_response):
        pass

    def test_update_to_previously_revised_response_updates_block(self, revised_response):
        pass

    def test_update_multiple_response(self, revised_response):
        pass

    def test_revert_updated_response_deletes_block(self, revised_response):
        pass

    def test_update_surfaced_by_all_response_property(self, initial_response):
        pass

    def test_update_surfaced_by_revised_response_keys_property(self, revised_response):
        pass

    def test_reverted_update_surfaced_by_revised_response_keys_property(self, revised_response):
        pass
