from nose.tools import *  # noqa
from tests.base import OsfTestCase

import json
from modularodm import Q

from framework.mongo.utils import to_mongo

from website.project.model import ensure_schemas, MetaSchema
from tests import factories
from scripts.migration.migrate_registered_meta import main as do_migration
from scripts.migration.migrate_registered_meta import get_old_registered_nodes

SCHEMA_NAMES = [
    'Open-Ended Registration',
    'OSF-Standard Pre-Data Collection Registration',
    'Replication Recipe (Brandt et al., 2013): Pre-Registration',
    'Replication Recipe (Brandt et al., 2013): Post-Completion'
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
}


class TestMigrateSchemas(OsfTestCase):
    def setUp(self):
        super(TestMigrateSchemas, self).setUp()

        MetaSchema.remove()
        ensure_schemas()

        self.open_ended_schema = MetaSchema.find_one(
            Q('name', 'eq', SCHEMA_NAMES[0]) &
            Q('schema_version', 'eq', 1)
        )
        self.open_ended = factories.RegistrationFactory(
            registered_meta={
                to_mongo(SCHEMA_NAMES[0]): json.dumps(OLD_META[SCHEMA_NAMES[0]])
            },
            registered_schema=self.open_ended_schema
        )
        del self.open_ended.registered_meta['Template1']
        self.open_ended.save()
        self.standard_schema = MetaSchema.find_one(
            Q('name', 'eq', SCHEMA_NAMES[1]) &
            Q('schema_version', 'eq', 1)
        )
        self.standard = factories.RegistrationFactory(
            registered_meta={
                to_mongo(SCHEMA_NAMES[1]): json.dumps(OLD_META[SCHEMA_NAMES[1]])
            },
            registered_schema=self.standard_schema
        )
        del self.standard.registered_meta['Template1']
        self.standard.save()
        self.brandt_pre_schema = MetaSchema.find_one(
            Q('name', 'eq', SCHEMA_NAMES[2]) &
            Q('schema_version', 'eq', 1)
        )
        self.brandt_pre = factories.RegistrationFactory(
            registered_meta={
                to_mongo(SCHEMA_NAMES[2]): json.dumps(OLD_META[SCHEMA_NAMES[2]])
            },
            registered_schema=self.brandt_pre_schema
        )
        del self.brandt_pre.registered_meta['Template1']
        self.brandt_pre.save()
        self.brant_post_schema = MetaSchema.find_one(
            Q('name', 'eq', SCHEMA_NAMES[3]) &
            Q('schema_version', 'eq', 1)
        )
        self.brandt_post = factories.RegistrationFactory(
            registered_meta={
                to_mongo(SCHEMA_NAMES[3]): json.dumps(OLD_META[SCHEMA_NAMES[3]])
            },
            registered_schema=self.brant_post_schema
        )
        del self.brandt_post.registered_meta['Template1']
        self.brandt_post.save()

    def test_get_old_registered_nodes(self):
        # create a non-registered node
        factories.NodeFactory()

        old_nodes = get_old_registered_nodes(dry_run=False)
        assert_equal(len(old_nodes), 4)

    def test_migrate_registration_schemas(self):
        target_nodes = get_old_registered_nodes(dry_run=False)
        do_migration(dry_run=False)

        for node in target_nodes:
            schema_name = node.registered_schema.name
            old_data = OLD_META[schema_name]
            for key, value in old_data.iteritems():
                assert_equal(node.registered_meta[key]['value'], value)
            assert_equal(node.registered_schema.schema_version, 2)
