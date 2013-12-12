"""
Ensure that all node IDs embedded in the analytics collections (page counters,
user activity counters) are lower-cased following GUID migration.

Examples:
    Dry run:
        python migrate_counters.py
    Real:
        python migrate_counters.py false

"""

import re
import logging
from pymongo.errors import DuplicateKeyError

from framework import db

logging.basicConfig(level=logging.DEBUG)

def migrate_pagecounters(dry_run=True):

    collection = db['pagecounters']

    for counter in collection.find():

        _id = counter['_id']

        match = re.search(r'node:(\w{5})$', _id)
        if match:
            nid = match.groups()[0]
            if nid == nid.lower():
                continue
            new_id = 'node:{}'.format(nid.lower())
            logging.debug('Changing _id {} to {}'.format(
                _id, new_id
            ))
            counter['_id'] = new_id
            if not dry_run:
                try:
                    collection.update({'_id': new_id}, counter, upsert=True)
                except DuplicateKeyError:
                    logging.debug('Key exists')

        match = re.search(r'download:(\w{5}):(.*)', _id)
        if match:
            nid, etc = match.groups()
            if nid == nid.lower():
                continue
            new_id = 'download:{}:{}'.format(nid.lower(), etc)
            logging.debug('Changing _id {} to {}'.format(
                _id, new_id
            ))
            counter['_id'] = new_id
            if not dry_run:
                try:
                    collection.update({'_id': new_id}, counter, upsert=True)
                except DuplicateKeyError:
                    logging.debug('Key exists')

def migrate_useractivitycounters(dry_run=True):

    collection = db['useractivitycounters']

    for counter in collection.find():

        _id = counter['_id']

        if _id == _id.lower():
            continue

        counter['_id'] = _id.lower()
        logging.debug('Changing _id {} to {}'.format(
            _id, _id.lower()
        ))
        if not dry_run:
            try:
                collection.update({'_id': _id.lower()}, counter, upsert=True)
            except DuplicateKeyError:
                logging.debug('Key exists')

if __name__ == '__main__':

    import sys
    try:
        dry_run = sys.argv[1].lower() not in ['f', 'false']
    except IndexError:
        dry_run = True

    migrate_pagecounters(dry_run=dry_run)
    migrate_useractivitycounters(dry_run=dry_run)
