"""
Changes existing registered_meta on a node to new schema layout
required for the prereg-prize
"""
from nose.tools import *  # noqa PEP8 asserts
import json
import sys
import logging

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.mongo import database as db
nodes = db['node']
from framework.mongo.utils import from_mongo
from framework.transactions.context import TokuTransaction

from website.models import Node, MetaSchema
from website.app import init_app
from website.project.model import ensure_schemas
from website.project.metadata.schemas import _id_to_name

from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def verify_migration(nodes, dev):
    for node in nodes:
        try:
            assert_is_not_none(node.registered_meta)
            assert_is_not_none(node.registered_schema)
            schema = node.registered_schema
            assert_greater(schema.version, 1)
        except AssertionError as e:
            if dev:
                logger.info("Node: {0} has no associated registered_schema.".format(node._id))
            else:
                raise e

def migrate_non_registered_nodes():
    nodes.update(
        {
            'registered_schema': None
        },
        {
            '$set': {
                'registered_schema': []
            }
        },
        multi=True
    )

def get_old_registered_nodes():
    return nodes.find({'is_registration': True})

def main(dry_run, dev=False):
    init_app(routes=False)
    count = 0
    skipped = 0
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
        logger.info("Iterating over all registrations")

    # nullify old registered_schema refs
    MetaSchema.remove(
        Q('schema_version', 'eq', 1)
    )
    ensure_schemas()

    node_documents = get_old_registered_nodes()
    for node in node_documents:
        registered_schemas = []
        registered_meta = {}
        schemas = node['registered_meta']
        if not schemas:
            logger.info('Node: {0} is registered but has no registered_meta'.format(node['_id']))
            schemas = {}
        for schema_id, schema in schemas.iteritems():
            name = _id_to_name(from_mongo(schema_id))
            # Unstringify stored metadata
            try:
                schema = json.loads(schema) if schema else {}
            except TypeError as e:
                if isinstance(schema, dict):
                    pass
                else:
                    raise e
            # append matching schema to node.registered_schema
            try:
                meta_schema = MetaSchema.find_one(
                    Q('name', 'eq', name) &
                    Q('schema_version', 'eq', 2)
                )
            except NoResultsFound:
                logger.error('No MetaSchema matching name: {0}, version: {1} found'.format(name, 2))
                # Skip over missing schemas
                skipped += 1
                continue
            else:
                registered_meta[meta_schema._id] = schema
                registered_schemas.append(meta_schema._id)
        nodes.update(
            {'_id': node['_id']},
            {
                '$set': {
                    'registered_schema': registered_schemas,
                    'registered_meta': registered_meta
                }
            }
        )
        count = count + 1
    logger.info('Done with {0} nodes migrated and {1} nodes skipped.'.format(count, skipped))
    migrate_non_registered_nodes()

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    dev = 'dev' in sys.argv
    with TokuTransaction():
        main(dry_run, dev)
        if dry_run:
            raise RuntimeError('Dry run, rolling back transaction.')
