"""
Changes existing registered_meta on a node to new schema layout
required for the prereg-prize
"""
import json
import sys
import logging

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.mongo.utils import from_mongo

from website.models import Node, MetaSchema
from website.app import init_app
from website.project.model import ensure_schemas
from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_old_registered_nodes(dry_run=True):
    if not dry_run:
        # nullify old registered_schema refs
        MetaSchema.remove(Q('schema_version', 'eq', 1))
        ensure_schemas()

    return Node.find(
        Q('is_registration', 'eq', True) &
        Q('registered_schema', 'eq', None)
    )

def main(dry_run):
    init_app(routes=False)
    count = 0
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
        logger.info("Iterating over all registrations")

    for node in get_old_registered_nodes(dry_run):
        schemas = node.registered_meta
        if not schemas:
            logger.info('Node: {0} is registered but has no registered_meta'.format(node._id))
            schemas = {}
        # there is only ever one key in this dict
        for name, schema in schemas.iteritems():
            name = from_mongo(name)

            schema = json.loads(schema)
            schema_data = {
                'embargoEndDate': schema.get('embargoEndDate', ''),
                'registrationChoice': schema.get('registrationChoice', ''),
            }
            schema_data.update(schema)
            try:
                meta_schema = MetaSchema.find_one(
                    Q('name', 'eq', name.replace('_', ' ')) &
                    Q('schema_version', 'eq', 2)
                )
            except NoResultsFound:
                logger.error('No MetaSchema matching name: {0}, version: {1} found'.format(name, 2))
                # Skip over missing schemas
                continue
            node.registered_schema = meta_schema
            node.registered_meta = {
                key: {
                    'value': value
                }
                for key, value in schema_data.iteritems()
            }
            if not dry_run:
                node.save()
        count = count + 1
    logger.info('Done with {} nodes migrated'.format(count))

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    main(dry_run)
