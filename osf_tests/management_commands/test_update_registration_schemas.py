import pytest

from osf.management.commands import update_registration_schemas
from osf.models import SchemaResponseBlock
from osf_tests.factories import RegistrationFactory


@pytest.mark.django_db
class TestUpdateRegistrationSchemas:

    @pytest.fixture
    def registration(self):
        return RegistrationFactory()

    def test_update_schemas_does_not_delete_schema_response_blocks(self, registration):
        initial_response_block_count = SchemaResponseBlock.objects.count()
        update_registration_schemas()
        assert SchemaResponseBlock.objects.count() == initial_response_block_count()

    def test_update_schemas_remaps_source_schema_block_for_response_blocks(self, registration):
        update_registration_schemas()
        for response_block in SchemaResponseBlock.objects.all():
            assert response_block.source_schema_block.exists()
            assert response_block.source_schema_block.registration_response_key == response_block.schema_key
            assert response_block.source_schema_block.schema == response_block.source_schema_response.schema
