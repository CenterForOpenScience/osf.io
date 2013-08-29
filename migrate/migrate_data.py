"""
Migrate schemas from yORM to ODM. Copies data from the database defined in
schema_yorm.py to the database defined in website/settings.py.
"""

import pprint
import time

from modularodm import StoredObject
from modularodm import fields
from modularodm import storage
from modularodm.query.querydialect import DefaultQueryDialect as Q

# Import ODM-style schemas from OSF
from framework.search.model import Keyword
from framework.auth.model import User
from website.project.model import Tag
from website.project.model import NodeLog
from website.project.model import NodeFile
from website.project.model import Node
from website.project.model import NodeWikiPage
from framework import db

# Import yORM-style schemas
import schema_yorm

# Schemas must be migrated in order to preserve relationships. This
# could be implemented using some kind of dependency tracking, but is
# done by hand for now.
schemas = [
    'Keyword',
    'User',
    'Tag',
    'NodeLog',
    'NodeFile',
    'Node',
    'NodeWikiPage',
]

raw_collections = [
    'pagecounters',
    'useractivitycounters',
]

# Migration

def _migrate_record(yorm, ODM, foreign=True):
    """Migrate one schema record from yORM to ODM.
    :param yorm: yORM record
    :param ODM: ODM schema
    :param foreign: Copy foreign fields?
    """

    odm = ODM.load(yorm[ODM._primary_name])
    if odm is None:
        odm = ODM()

    for key, val in yorm.items():
        if key == '_doc' or key.startswith('_b_'):
            continue
        if key not in odm._fields:
            continue
        field_object = odm._fields[key]
        if field_object._is_foreign and not foreign:
            setattr(odm, key, field_object._gen_default())
        else:
            setattr(odm, key, val)
    odm._is_optimistic = False

    # Skip records with missing PK
    if isinstance(odm._primary_key, odm._primary_type):
        odm.save()

def _migrate(YORM, ODM, foreign):
    """Migrate a schema from yORM to ODM, optionally copying foreign fields.
    :param YORM: yORM schema
    :param ODM: ODM schema
    :param foreign: Copy foreign fields?
    """

    yorms = YORM.find()
    for yorm in yorms:
        _migrate_record(yorm, ODM, foreign=foreign)

def migrate(YORM, ODM):
    """Migrate a schema from yORM to ODM.
    :param YORM: yORM schema
    :param ODM: ODM schema
    """

    # Must run _migrate twice if self-referential
    self_reference = False
    for field_name, field_object in ODM._fields.items():
        if field_object._is_foreign \
                and field_object.base_class._name == ODM._name:
            self_reference = True

    if self_reference:
        _migrate(YORM, ODM, foreign=False)
    _migrate(YORM, ODM, foreign=True)

def migrate_schemas():

    migrate_time = {}
    t0_all = time.time()

    for schema in schemas:

        db[schema.lower()].remove()

        _schema_yorm = getattr(schema_yorm, schema)
        _schema_odm = globals()[schema]

        t0_schema = time.time()
        migrate(_schema_yorm, _schema_odm)
        migrate_time[schema] = time.time() - t0_schema

    migrate_time['ALL'] = time.time() - t0_all

    pprint.pprint(migrate_time)

def migrate_raw():
    for collection_name in raw_collections:
        old_records = schema_yorm.db[collection_name].find()
        db[collection_name].remove()
        db[collection_name].insert(old_records)

def migrate_all():

    migrate_raw()
    migrate_schemas()
