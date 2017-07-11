"""Comment.root_target should always point to a Guid. A few comments on production were missed by a migration and point
to TrashedFileNodes and restored StoredFileNodes instead. This migration points the root_target to the Guids for
those TrashedFileNodes.
"""
import logging
import sys

from modularodm import Q
from modularodm.exceptions import ModularOdmException

from framework.guid.model import Guid
from framework.transactions.context import TokuTransaction
from website.models import Comment, StoredFileNode, TrashedFileNode
from website.app import init_app

from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def get_file_node(_id):
    # First check the storedfilenode collection
    filenode = StoredFileNode.load(_id)
    # If no record in storedfilenode, try trashedfilenode
    if not filenode:
        filenode = TrashedFileNode.load(_id)
    if not filenode:
        logger.error('Could not find storedfilenode or trashedfilenode with id {}'.format(_id))
    else:
        logger.info('Found filenode: {}'.format(filenode._id))
    return filenode

def get_guid(filenode):
    try:
        guid = Guid.find_one(Q('referent', 'eq', filenode))
    except ModularOdmException:
        logger.error('No Guid found for filenode {}'.format(filenode._id))
        return None
    else:
        return guid

def main():
    query = Comment.find(Q('root_target.1', 'ne', 'guid'))
    logger.info('Found {} comments whose root target is not a guid'.format(query.count()))
    migrated = 0
    for comment in query:
        root_target = comment.to_storage()['root_target']
        if root_target:
            logger.info('Root target for comment {}: {}'.format(comment._id, root_target))
            _id, collection = root_target
            if collection == 'storedfilenode':
                filenode = get_file_node(_id)
                if filenode:
                    guid = get_guid(filenode)
                    if guid:
                        logger.info('Setting root_target to Guid {}'.format(guid._id))
                        comment.root_target = guid
                        comment.save()
                        migrated += 1
            else:
                logger.error('Unexpected root target: {}'.format(root_target))
        # If root_target is unset, look at the target field
        elif root_target is None:
            logger.info('Root target for comment {} is None'.format(comment._id))
            guid = comment.target
            if isinstance(guid.referent, (TrashedFileNode, StoredFileNode)):
                logger.info('Setting root_target to Guid {}'.format(guid._id))
                comment.root_target = guid
                comment.save()
                migrated += 1
            elif isinstance(guid.referent, Comment):
                logger.info('Comment {} has a comment target. It is a reply.'.format(comment._id))
                found_root = False
                parent = guid.referent
                while not found_root:
                    if not isinstance(parent.target.referent, Comment):
                        found_root = True
                    else:
                        parent = parent.target.referent
                guid = parent.target
                logger.info('Setting root_target to Guid {}'.format(guid._id))
                comment.root_target = guid
                comment.save()
                migrated += 1

    logger.info('Successfully migrated {} comments'.format(migrated))


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    with TokuTransaction():
        main()
        if dry:
            raise Exception('Dry Run -- Aborting Transaction')
