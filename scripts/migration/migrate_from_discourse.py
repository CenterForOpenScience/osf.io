import os
import sys
import shutil
import tempfile
import json
import logging

from framework import discourse
from website import models, files
from website.addons import wiki
from website.app import init_app
from modularodm import Q

logger = logging.getLogger(__name__)

def import_discourse_ids(in_file, dry_run):
    for json_line in in_file:
        obj = json.loads(json_line)
        target = models.Guid.find(Q('_id', 'eq', obj['guid']))[0].referent
        if obj['type'] == 'user':
            target.discourse_user_id = obj['user_id']
            target.discourse_user_created = True
        elif obj['type'] == 'project':
            target.discourse_group_id = obj['group_id']
            target.discourse_group_public = obj['group_public']
            target.discourse_group_users = obj['group_users']
        elif obj['type'] == 'topic':
            target.discourse_topic_id = obj['topic_id']
            target.discourse_topic_title = obj['topic_title']
            target.discourse_topic_parent_guids = obj['topic_parent_guids']
            target.discourse_topic_deleted = obj['topic_deleted']
            target.discourse_post_id = obj['post_id']
        if not dry_run:
            target.save()

def main():
    if len(sys.argv) != 2 and len(sys.argv) != 3:
        sys.exit('Usage: %s input_file [--dry]' % sys.argv[0])

    dry_run = False
    if '--dry' in sys.argv:
        dry_run = True
        logger.warn('Dry_run mode')

    in_file = open(sys.argv[1], 'r')
    init_app(set_backends=True, routes=False)
    import_discourse_ids(in_file, dry_run)

if __name__ == '__main__':
    main()
