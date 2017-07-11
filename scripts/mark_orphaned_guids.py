"""A number of GUIDs with invalid or missing referents
were found during the mongo -> postgres migration.
These GUIDS were parsed from the migration logs and written to scripts/orphaned_guids.json.

This script adds a field, `is_orphaned` to these GUIDS and sets it to True so that they
can be skipped during the mongo -> postgres migration.
"""
import json
import sys
import os
import logging

from scripts import utils as script_utils
from framework.mongo import database


logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))

def main(dry=True):
    with open(os.path.join(HERE, 'orphaned_guids.json'), 'r') as fp:
        orphaned_guids = json.load(fp)
    for collection_name, guids in orphaned_guids.iteritems():
        logger.info('Updating {} GUIDs that point to the collection: {}'.format(
            len(guids), collection_name
        ))
        if not dry:
            database.guid.update(
                {'_id': {'$in': guids}},
                {'$set': {'is_orphaned': True}},
                multi=True
            )


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(name)s]  %(levelname)s: %(message)s',
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
