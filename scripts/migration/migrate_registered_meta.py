"""
Changes existing registered_meta on a node to new schema layout
required for the prereg-prize
"""
import json
import sys
import logging

from modularodm import Q

from framework.mongo import database as db
from framework.mongo.utils import from_mongo
from framework.transactions.context import TokuTransaction

from website.models import MetaSchema
from website.app import init_app
from website.project.model import ensure_schemas
from website.project.metadata.schemas import _id_to_name

from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def prepare_nodes(_db=None):
    _db = _db or db
    _db['node'].update(
        {},
        {
            '$set': {
                'registered_schema': []
            }
        },
        multi=True
    )

def from_json_or_fail(schema):
    # Unstringify stored metadata
    try:
        schema = json.loads(schema) if schema else {}
    except TypeError as e:
        if isinstance(schema, dict):
            pass
        else:
            raise e
    return schema

def main(dev=False, _db=None):
    _db = _db or db
    init_app(routes=False)
    count = 0
    skipped = 0
    scripts_utils.add_file_logger(logger, __file__)
    logger.info("Iterating over all registrations")

    # convert registered_schema to list field
    prepare_nodes()
    ensure_schemas()

    node_documents = _db['node'].find({'is_registration': True})
    for node in node_documents:
        registered_schemas = []
        registered_meta = {}
        schemas = node['registered_meta']
        if not schemas:
            logger.info('Node: {0} is registered but has no registered_meta'.format(node['_id']))
            continue
        for schema_id, schema in schemas.iteritems():
            name = _id_to_name(from_mongo(schema_id))
            schema = from_json_or_fail(schema)
            # append matching schema to node.registered_schema
            try:
                meta_schema = MetaSchema.find(
                    Q('name', 'eq', name)
                ).sort('-schema_version')[0]
            except IndexError as e:
                logger.error('No MetaSchema matching name: {0} found for node: {1}.'.format(name, node['_id']))
                # Skip over missing schemas
                skipped += 1
                if dev:
                    continue
                else:
                    raise e
            else:
                registered_meta[meta_schema._id] = {
                    key: {
                        'value': value
                    }
                    for key, value in schema.items()
                }
                registered_schemas.append(meta_schema._id)
        db['node'].update(
            {'_id': node['_id']},
            {'$set': {
                'registered_meta': registered_meta,
                'registered_schema': registered_schemas
            }}
        )
        count = count + 1
    logger.info('Done with {0} nodes migrated and {1} nodes skipped.'.format(count, skipped))

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    dev = 'dev' in sys.argv
    with TokuTransaction():
        main(dev=dev)
        if dry_run:
            raise RuntimeError('Dry run, rolling back transaction.')
