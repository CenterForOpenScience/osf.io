""" Changes existing registered_meta on a node to new schema layout
required for the prereg-prize
"""
import re
import json
import sys
import logging

from modularodm import Q

from website.models import Node
from website.app import init_app
from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
IMMUTABLE_KEYS = frozenset(['datacompletion', 'summary'])

def get_registered_nodes():
    return Node.find(
        Q('is_registration', 'eq', True) &
        Q('fits_prereg_schema', 'eq', False)
    )


def main(dry_run):
    init_app(routes=False)
    count = 0

    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
        logger.info("Iterating over all registrations")

    new_registration_data = dict()
    for node in get_registered_nodes():
        for schema, schema_data in json.loads(node.registered_meta).items():
            valid_schema = {
                'embargoEndDate': schema_data['embargoEndDate'] if 'embargoEndDate' in schema_data else '',
                'registrationChoice': schema_data['registrationChoice'] if 'registrationChoice' in schema_data else '',
            }

            # in most schemas, answers are just stored as { 'itemX': 'answer' }
            # only 'datacompletion' and 'summary' are stored with their name
            # and can be interspersed with the itemX keys so reassigning keys based on num_questions
            # could cause conflicts. Instead they are left there.
            matches = dict()
            for val in schema_data:
                match = re.search("item[0-9]*", val)
                if match is not None and val not in IMMUTABLE_KEYS:
                    new_val = val.replace('q', 'item')
                    matches[new_val] = schema_data[val]

            if matches:
                for item_num, item in matches.iteritems():
                    # if already matches the schema, don't change anything
                    if isinstance(item, dict):
                        valid_schema[item_num] = {
                            'value': item['value'] if 'value' in item else '',
                            'comments': item['comments'] if 'comments' in item else {}
                        }

                    # everything else that doesn't match
                    else:
                        valid_schema[item_num] = {
                            'comments': {},
                            'value': item
                        }

            new_registration_data[schema] = valid_schema
            count += 1

        if not dry_run:
            node.registered_meta = new_registration_data
            node.fits_prereg_schema = True
            node.save()

    logger.info('Done with {} nodes migrated'.format(count))

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    main(dry_run)
