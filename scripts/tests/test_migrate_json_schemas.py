from nose.tools import *
from tests.base import OsfTestCase

from website.models import MetaSchema
from website.project.metadata.schemas import OSF_META_SCHEMAS
from scripts.migration.migrate_json_schemas import main as do_migration


class TestMigrateSchemas(OsfTestCase):
    def setUp(self):
        super(TestMigrateSchemas, self).setUp()
        self.schemas = [schema for schema in OSF_META_SCHEMAS]

    def test_migrate_json_schemas(self):
        do_migration()
        for schema in MetaSchema.find():
            assert_in('name', schema)
            assert_in('version', schema)
            assert_equal(schema['type'], 'object')
            assert_in('description', schema)
            assert_in('fulfills', schema)
            assert_in('pages', schema)
            assert_in('id', schema['pages'])
            assert_in('title', schema['pages'])
            assert_equal(schema['pages']['type'], 'object')
            assert_in('properties', schema['pages'])

