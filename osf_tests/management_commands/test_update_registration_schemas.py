import copy
from unittest import mock
import random
import pytest

from osf.management.commands import update_registration_schemas
from osf.models import RegistrationSchema, RegistrationSchemaBlock
from osf_tests.default_test_schema import DEFAULT_TEST_SCHEMA, DEFAULT_TEST_SCHEMA_NAME
from website.project.metadata.schemas import get_osf_meta_schemas


@pytest.mark.django_db
class TestUpdateRegistrationSchemas:

    @pytest.fixture
    def updated_schema(self):
        known_schemas = get_osf_meta_schemas()
        schema_to_update = copy.deepcopy(random.choice(known_schemas))
        # some schemas have multiple versions present in get_osf_metaschemas
        # increment by a silly number to account for this
        schema_to_update['version'] += 100
        return schema_to_update

    def test_update_schemas_creates_new_schemas(self, updated_schema):
        assert not RegistrationSchema.objects.filter(
            name=DEFAULT_TEST_SCHEMA_NAME
        ).exists()
        assert not RegistrationSchema.objects.filter(
            name=(updated_schema.get('title') or updated_schema.get('name')),
            schema_version=updated_schema['version']
        ).exists()

        test_schemas = get_osf_meta_schemas() + [updated_schema, DEFAULT_TEST_SCHEMA]
        with mock.patch.object(
            update_registration_schemas.migrations,
            'get_osf_meta_schemas',
            return_value=test_schemas
        ):
            update_registration_schemas.update_registration_schemas()

        assert RegistrationSchema.objects.filter(
            name=DEFAULT_TEST_SCHEMA_NAME
        ).exists()
        assert RegistrationSchema.objects.filter(
            name=updated_schema.get('name'),
            schema_version=updated_schema['version']
        ).exists()

    def test_update_schemas_only_creates_schemablocks_for_new_schemas(self, updated_schema):
        assert not RegistrationSchemaBlock.objects.filter(
            schema__name=DEFAULT_TEST_SCHEMA_NAME
        ).exists()
        assert not RegistrationSchemaBlock.objects.filter(
            schema__name=updated_schema.get('name'),
            schema__schema_version=updated_schema['version']
        ).exists()

        initial_block_ids = set(RegistrationSchemaBlock.objects.values_list('id', flat=True))
        test_schemas = get_osf_meta_schemas() + [updated_schema, DEFAULT_TEST_SCHEMA]
        with mock.patch.object(
            update_registration_schemas.migrations,
            'get_osf_meta_schemas',
            return_value=test_schemas
        ):
            update_registration_schemas.update_registration_schemas()

        block_ids_for_new_schema = set(
            RegistrationSchemaBlock.objects.filter(
                schema__name=DEFAULT_TEST_SCHEMA_NAME
            ).values_list('id', flat=True)
        )
        assert block_ids_for_new_schema

        block_ids_for_updated_schema = set(
            RegistrationSchemaBlock.objects.filter(
                schema__name=(updated_schema.get('title') or updated_schema.get('name')),
                schema__schema_version=updated_schema['version']
            ).values_list('id', flat=True)
        )
        assert block_ids_for_updated_schema

        expected_block_ids = (
            initial_block_ids
            | block_ids_for_new_schema
            | block_ids_for_updated_schema
        )
        all_block_ids = set(RegistrationSchemaBlock.objects.values_list('id', flat=True))
        assert all_block_ids == expected_block_ids
