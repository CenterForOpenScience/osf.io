"""

First run the following in a mongo shell:

    db.getCollection('boxnodesettings').update({'user_settings': {'$type': 2}}, {$rename: { user_settings: 'foreign_user_settings'}}, {multi: true})

Then change the user_settings field of BoxNodeSettings to foreign_user_settings
"""
import sys
import logging

from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.addons.box.model import BoxNodeSettings

logger = logging.getLogger('migrate_user_settings_field')

def do_migration():
    for node in BoxNodeSettings.find():
        if node.foreign_user_settings is None:
            continue
        logger.info('Migrating user_settings for box {}'.format(node._id))
        node.user_settings = node.foreign_user_settings
        node.save()

def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models
    with TokuTransaction():
        do_migration()
        if dry:
            raise Exception('Abort Transaction - Dry Run')

if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
