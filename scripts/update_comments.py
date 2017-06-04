"""
Update User.comments_viewed_timestamp field.
"""
import logging
import sys

from modularodm import Q

from framework.auth.core import User
from framework.transactions.context import TokuTransaction

from website.models import Comment
from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def main():
    update_comments_viewed_timestamp()


def update_comments_viewed_timestamp():
    users = User.find(Q('comments_viewed_timestamp', 'ne', None) & Q('comments_viewed_timestamp', 'ne', {}))
    for user in users:
        if user.comments_viewed_timestamp:
            timestamps = {}
            dirty = False
            for node_id in user.comments_viewed_timestamp:
                node_timestamps = user.comments_viewed_timestamp[node_id]

                if isinstance(node_timestamps, dict):
                    # node timestamp
                    if node_timestamps.get('node', None):
                        timestamps[node_id] = node_timestamps['node']
                        dirty = True

                    # file timestamps
                    file_timestamps = node_timestamps.get('files', None)
                    if file_timestamps:
                        for file_id in file_timestamps:
                            timestamps[file_id] = file_timestamps[file_id]
                            dirty = True
                else:
                    timestamps[node_id] = node_timestamps

            if dirty:
                user.comments_viewed_timestamp = timestamps
                user.save()
                logger.info('Migrated timestamp for user {0}'.format(user._id))


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, set_backends=True)
    with TokuTransaction():
        main()
        if dry:
            raise Exception('Dry Run -- Aborting Transaction')
