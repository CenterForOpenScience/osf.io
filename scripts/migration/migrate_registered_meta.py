""" Changes existing registered_meta on a node to new schema layout
required for the prereg-prize
"""
import re
import ast
import sys
import logging

from nose.tools import *
from modularodm import Q

from website import models
from website.app import init_app
from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_registered_nodes():
    return models.Node.find(
        Q('is_registration', 'eq', True)
    )


def main(dry_run=True):
    init_app(routes=False)
    count = 0

    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
        logger.info("Iterating over all registrations")
        models.MetaSchema.remove()

    for node in get_registered_nodes():
        for schema in node.registered_meta:
            values = ast.literal_eval(node.registered_meta.get(schema))

            valid_schema = {
                'embargoEndDate': values['embargoEndDate'],
                'registrationChoice': values['registrationChoice']
            }

            # in most schemas, answers are just stored as { 'itemX': 'answer' }
            matches = dict()
            for val in values:
                m = re.search("item[0-9]*", val)
                if m is not None or val == 'datacompletion' or val == 'summary':
                    p = re.compile(r'item')
                    new_val = p.sub('q', val)
                    matches[new_val] = values[val]

            if matches:
                for item_num, item in matches.iteritems():
                    if isinstance(value, dict):
                        valid_schema[item_num] = {
                            'value': value['value'] if 'value' in value else '',
                            'comments': value['comments'] if 'comments' in value else {}
                        }
                    else:
                        valid_schema[item_num] = {
                            'comments': {},
                            'value': value
                        }

        count += 1

        if not dry_run:
            node.registered_meta[schema] = valid_schema
            node.save()

    logger.info('Done with {} nodes migrated'.format(count))


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    main()
