import ast
from nose.tools import *
from tests.base import OsfTestCase

from modularodm import Q
from website.models import Node
from tests.factories import NodeFactory
from scripts.migration.migration_registered_meta import main as do_migration


class TestMigrateSchemas(OsfTestCase):
    def setUp(self):
        super(TestMigrateSchemas, self).setUp()
        self.reg1 = NodeFactory(is_registration=True, registered_meta={u'Open-Ended_Registration': u'{"registrationChoice": \
         "immediate","embargoEndDate":"Thu%2C 02 Jul 2015 00%3A08%3A22 GMT","summary":\
          "This is the most basic schema that we have"}'}
                                )
        self.reg2 = NodeFactory(is_registration=True, registered_meta={u'V serious Registration': u'{"embargoEndDate":\
            "Thu%2C 02 Jul 2015 13%3A34%3A27 GMT","item1": "the nature","item10": "yes","item11": "asfd","item12":\
            "fasfsdf","item13": "has anyone","item14": "even been so","item15": "far as","item16": "decided to use",\
            "item17": "Close","item18": "Exact","item19": "Exact","item2": "of the ","item22": "Different","item23":\
            "Different","item24": " even go want","item25": " to do look more like%3F","item26": "You%27ve got to\
            be kidding me. ","item27": "I%27ve been further even more decided to use even go need to do look more as\
            anyone can. C","item28": "an you really be far even as decided half as much to use go wish for that%3F",\
            "item3": "effect","item4": "is so","item5": "huge","item6": "i need to see","item7": "these ","item8":\
            "answers","item9": "wtf","registrationChoice": "immediate"}'
                                                                       })

    def test_migrate_json_schemas(self):
        do_migration(dry_run=False)
        migrated_nodes = Node.find(
            Q('is_registration', 'eq', True)
        )

        for node in migrated_nodes:
            data = node.registered_meta
            pages = data['pages']

            assert_in('name', data)
            assert_in('fulfills', data)
            assert_in('description', data)
            assert_equal(data['type'], 'object')
            assert_in('version', data)
            assert_in('pages', data)
            assert_in('questions', pages[0])
            assert_in('id', pages[0])
            assert_in('title', pages[0])
            assert_equal(pages[0]['type'], 'object')
            assert_in('properties', pages[0]['questions'][0])
