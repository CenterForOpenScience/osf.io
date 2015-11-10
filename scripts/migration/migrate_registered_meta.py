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

from framework.mongo.utils import from_mongo
from framework.transactions.context import TokuTransaction

from website.models import Node, MetaSchema
from website.app import init_app
from website.project.model import ensure_schemas
from website.project.metadata.schemas import _name_to_id

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

def get_old_registered_nodes():
    # nullify old registered_schema refs
    MetaSchema.remove(Q('schema_version', 'eq', 1))
    ensure_schemas()

    return Node.find(
        Q('is_registration', 'eq', True)
    )

def main(dry_run, dev=False):
    init_app(routes=False)
    count = 0
    skipped = 0
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
        logger.info("Iterating over all registrations")

    nodes = get_old_registered_nodes()
    for node in nodes:
        schemas = node.registered_meta
        if not schemas:
            logger.info('Node: {0} is registered but has no registered_meta'.format(node._id))
            schemas = {}
            node.registered_meta = {}
        # there is only ever one key in this dict
        for name, schema in schemas.iteritems():
            name = from_mongo(name)

            try:
                schema = json.loads(schema) if schema else {}
            except TypeError as e:
                if isinstance(schema, dict):
                    pass
                else:
                    raise e
            schema_data = {
                'embargoEndDate': schema.get('embargoEndDate', ''),
                'registrationChoice': schema.get('registrationChoice', ''),
            }
            schema_data.update(schema)
            try:
                meta_schema = MetaSchema.find_one(
                    Q('name', 'eq', _name_to_id(name)) &
                    Q('schema_version', 'eq', 2)
                )
            except NoResultsFound:
                logger.error('No MetaSchema matching name: {0}, version: {1} found'.format(name, 2))
                # Skip over missing schemas
                skipped += 1
                continue
            node.registered_schema = meta_schema
            node.registered_meta = {
                key: {
                    'value': value
                }
                for key, value in schema_data.iteritems()
            }
        try:
            node.save()
        except TypeError as e:
            logger.info('TypeError when saving node ({0}): {1}'.format(node._id, e.message))
            if not dev:
                raise e
        except AttributeError as e:
            logger.info('AttributeError when saving node ({0}): {1}'.format(node._id, e.message))
            if not dev:
                raise e
        count = count + 1
    verify_migration(nodes, dev)
    logger.info('Done with {0} nodes migrated and {1} nodes skipped.'.format(count, skipped))

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    dev = 'dev' in sys.argv
    with TokuTransaction():
        main(dry_run, dev)
        if dry_run:
            raise RuntimeError('Dry run, rolling back transaction.')
