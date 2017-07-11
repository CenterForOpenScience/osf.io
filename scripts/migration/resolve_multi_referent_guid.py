import argparse
from datetime import datetime
import json
import logging
import re

from framework.mongo import database
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app
from website.models import Guid, Node

logger = logging.getLogger(__name__)


def fix_backrefs(node):
    if node._backrefs.get('addons', {}).get('addonfilesnodesettings'):
        database['node'].find_and_modify(
            {'_id': node._id},
            {'$unset': {
                '__backrefs.addons.addonfilesnodesettings': ''
            }}
        )
    if node._backrefs.get('uploads', {}).get('nodefile'):
        database['node'].find_and_modify(
            {'_id': node._id},
            {'$unset': {
                '__backrefs.uploads.nodefile': ''
            }}
        )

def clean_dict(doc):
    if '_id' in doc:
        doc.pop('_id')
    if '__backrefs' in doc:
        # Should not be touched
        doc.pop('__backrefs')
    if 'file_guid_to_share_uuids' in doc:
        # UUID's aren't JSON-serializable
        doc.pop('file_guid_to_share_uuids')
    for k, v in list(doc.iteritems()):
        # Nor are datetimes
        if isinstance(v, datetime):
            doc.pop(k)
        if isinstance(v, dict):
            doc[k] = clean_dict(v)
    return doc

def migrate(targets):
    collections = targets.pop('collections')
    assert len(targets), 'Must specify object to create new guid for'
    assert len(targets) == 1, 'Can only create new guid for one object at a time'
    old_id = targets.values()[0]
    node = Node.load(old_id)
    new_guid = Guid.generate(referent=node)
    logger.info('* Created new guid {} for node {}'.format(new_guid._id, old_id))
    logger.info('* Preparing to set references.')
    fix_backrefs(node)
    node.reload()
    node._id = new_guid._id
    node.save()
    new_guid.referent = node
    new_guid.save()

    for collection, _id_list in collections.iteritems():
        assert type(_id_list) == list, 'Expected type list for collection {} ids, got {}'.format(collection, type(_id_list))
        for _id in _id_list:
            logger.info('** Updating {} ({})'.format(_id, collection))
            doc = clean_dict(database[collection].find_one({'_id': _id}))
            replacement = json.loads(re.sub(r'\b{}\b'.format(old_id), new_guid._id, json.dumps(doc)))
            database[collection].find_and_modify(
                {'_id': _id},
                {'$set': replacement}
            )
            logger.info('*** Updated {} ({}): \n{}\n'.format(_id, collection, replacement))

    logger.info('Successfully migrate {} to {}'.format(old_id, new_guid._id))

def main():
    parser = argparse.ArgumentParser(
        description='Changes the guid of specified object and updates references in provided targets'
    )
    parser.add_argument(
        '--dry',
        action='store_true',
        dest='dry_run',
        help='Run migration and roll back changes to db',
    )
    parser.add_argument(
        '--targets',
        action='store',
        dest='targets',
        help="""Target JSON, of form
        {
          'data': {
            'node': <target_id>',  # Currently only supports nodes as target objects for new guids
            'collections': {
              '<collection>': [<_ids to update>]
            }
          }
        }
        """,
    )
    pargs = parser.parse_args()
    if not pargs.dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(targets=json.loads(pargs.targets)['data'])
        if pargs.dry_run:
            raise RuntimeError('Dry run, transaction rolled back.')

if __name__ == "__main__":
    main()
