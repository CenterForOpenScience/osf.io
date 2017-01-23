"""

First run the following in a mongo shell:

    db.getCollection('addondataversenodesettings').update({'user_settings': {'$type': 2}}, {$rename: { user_settings: 'foreign_user_settings'}}, {multi: true})

Then change the user_settings field of AddonDataverseNodeSettings to foreign_user_settings
"""
import sys
import logging

from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

from website.app import init_app
from addons.dataverse.model import AddonDataverseNodeSettings

logger = logging.getLogger('migrate_user_settings_field')

def do_migration():
    for dvs in AddonDataverseNodeSettings.find():
        if dvs.foreign_user_settings is None:
            continue
        logger.info('Migrating user_settings for dataverse {}'.format(dvs._id))
        dvs.user_settings = dvs.foreign_user_settings
        dvs.save()

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
