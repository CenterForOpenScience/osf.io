from nose.tools import *  # noqa
from tests.base import OsfTestCase

import json
from modularodm import Q

from framework.mongo.utils import to_mongo

from website.project.model import ensure_schemas, MetaSchema, Node
from tests import factories
from scripts.migration.migrate_registered_meta import (
    main as do_migration,
    prepare_nodes
)

SCHEMA_NAMES = [
    'Open-Ended Registration',
    'OSF-Standard Pre-Data Collection Registration',
    'Replication Recipe (Brandt et al., 2013): Pre-Registration',
    'Replication Recipe (Brandt et al., 2013): Post-Completion',
    'Confirmatory - General'
]
OLD_META = {
    'Open-Ended Registration': {
        'summary': 'some airy',
    },
    'OSF-Standard Pre-Data Collection Registration': {
        'comments': 'Standard',
        'datacompletion': 'Yes',
        'looked': 'Yes',
    },
    'Replication Recipe (Brandt et al., 2013): Pre-Registration': {
        'item1': 'Ver',
        'item10': 'yes',
        'item11': 'fas',
        'item12': 'afs',
        'item13': 'fsa',
        'item14': 'fsa',
        'item15': 'fsa',
        'item16': 'sf',
        'item17': 'Exact',
        'item18': 'Different',
        'item19': 'Different',
        'item2': 'vsf',
        'item20': 'Different',
        'item21': 'Close',
        'item22': 'Exact',
        'item23': 'Exact',
        'item24': 'fsasf',
        'item25': 'asfsfa',
        'item26': 'safasf',
        'item27': 'asf',
        'item28': 'fassf',
        'item3': 'fafa',
        'item4': 'fsafds',
        'item5': 'fafa',
        'item6': 'asdfsadf',
        'item7': 'sfsaf',
        'item8': 'sfdsdf',
        'item9': 'sfd',
    },
    'Replication Recipe (Brandt et al., 2013): Post-Completion': {
        'item29': 'adad',
        'item30': 'asd',
        'item31': 'asd',
        'item32': 'not significantly different from the original effect size',
        'item33': 'informative failure to replicate',
        'item34': 'asdasd',
        'item35': 'ds',
        'item36': 'ads',
        'item37': 'das',
    },
    'Confirmatory - General': {
        'comments': 'Standard',
        'datacompletion': 'Yes',
        'looked': 'Yes',
    }
}


class TestMigrateSchemas(OsfTestCase):

    def _make_registration(self, schemas):
        if not isinstance(schemas, list):
            schemas = [schemas]
        reg = factories.RegistrationFactory()
        reg.save()
        self.db['node'].update(
            {'_id': reg._id},
            {
                '$set': {
                    'registered_meta': {
                        to_mongo(schema.name): json.dumps(OLD_META[schema.name])
                        for schema in schemas
                    },
                    'registered_schema': None
                }
            }
        )

    def setUp(self):
        super(TestMigrateSchemas, self).setUp()

        MetaSchema.remove()
        ensure_schemas()

        self.regular_old_node = factories.NodeFactory()

        self.open_ended_schema = MetaSchema.find_one(
            Q('name', 'eq', SCHEMA_NAMES[0]) &
            Q('schema_version', 'eq', 1)
        )
        self.open_ended = self._make_registration(self.open_ended_schema)

        self.standard_schema = MetaSchema.find_one(
            Q('name', 'eq', SCHEMA_NAMES[1]) &
            Q('schema_version', 'eq', 1)
        )
        self.standard = self._make_registration(self.standard_schema)

        self.brandt_pre_schema = MetaSchema.find_one(
            Q('name', 'eq', SCHEMA_NAMES[2]) &
            Q('schema_version', 'eq', 1)
        )
        self.brandt_pre = self._make_registration(self.brandt_pre_schema)

        self.brandt_post_schema = MetaSchema.find_one(
            Q('name', 'eq', SCHEMA_NAMES[3]) &
            Q('schema_version', 'eq', 1)
        )
        self.brandt_post = self._make_registration(self.brandt_post_schema)

        self.multiple = self._make_registration([
            self.brandt_pre_schema,
            self.brandt_post_schema
        ])

        self.confirmatory_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Confirmatory - General')
        )
        self.confirmatory = self._make_registration(self.confirmatory_schema)

        self.db['node'].update({}, {'$set': {'registered_schema': None}}, multi=True)

    def tearDown(self):
        super(TestMigrateSchemas, self).tearDown()
        self.db['node'].remove()

    def test_prepare_nodes(self):
        prepare_nodes(self.db)
        for node in self.db['node'].find():
            assert_equal(node['registered_schema'], [])

    def test_migrate_registration_schemas(self):
        target_nodes = self.db['node'].find({'is_registration': True})
        do_migration(_db=self.db)

        for node in target_nodes:
            for meta_schema_id in node['registered_schema']:
                meta_schema = MetaSchema.load(meta_schema_id)
                old_data = OLD_META[meta_schema.name]
                for key, value in old_data.iteritems():
                    assert_equal(
                        node['registered_meta'][meta_schema._id][key]['value'],
                        value
                    )
