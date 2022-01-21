import pytest
import random

from osf.management.commands.update_registration_schemas import update_registration_schemas
from osf.models import RegistrationSchema, RegistrationSchemaBlock, SchemaResponseBlock
from osf_tests.factories import RegistrationFactory


@pytest.mark.django_db
class TestUpdateRegistrationSchemas:

    @pytest.fixture
    def registrations(self):
        schemas = RegistrationSchema.objects.all()
        for _ in range(20):
            schema = random.choice(schemas)
            RegistrationFactory(schema=schema)

    def test_update_schemas_rebuilds_schema_blocks(self, registrations):
        initial_schema_blocks = set(RegistrationSchemaBlock.objects.all())
        update_registration_schemas()
        new_schema_blocks = set(RegistrationSchemaBlock.objects.all())
        assert len(new_schema_blocks) == len(initial_schema_blocks)
        assert (new_schema_blocks & initial_schema_blocks) == set()

    def test_update_schemas_does_not_delete_schema_response_blocks(self, registrations):
        initial_response_blocks = set(SchemaResponseBlock.objects.all())
        update_registration_schemas()
        assert set(SchemaResponseBlock.objects.all()) == initial_response_blocks

    def test_update_schemas_remaps_source_schema_block_for_response_blocks(self, registrations):
        update_registration_schemas()
        for response_block in SchemaResponseBlock.objects.all():
            assert RegistrationSchemaBlock.objects.filter(id=response_block.source_schema_block_id).exists()
            assert response_block.source_schema_block.registration_response_key == response_block.schema_key
            assert response_block.source_schema_block.schema == response_block.source_schema_response.schema
