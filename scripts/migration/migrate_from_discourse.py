# There are three separate scripts used in migrating comments from the OSF to Discourse
# The first script is in the OSF, it can be run as
# (1) python -m scripts.migration.migrate_to_discourse export_file
# This file can then be imported to Discourse with
# (2) bundle exec ruby script/import_scripts/osf.rb export_file return_file
# which will create all of the users, categories, groups/projects, and topics
# that were exported from the osf. The return file contains id numbers for these
# various entities that the OSF will need to refer to them. These id numbers
# are then reimported back into the OSF with
# (3) python -m scripts.migration.migrate_from_discourse return_file
# Because the osf.rb import script does not exist in the actual discourse docker container
# The script will have to be manually added into script/import_scripts directory before executing

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

    discourse.common.in_migration = True
    import_discourse_ids(in_file, dry_run)
    discourse.common.in_migration = False

if __name__ == '__main__':
    main()
