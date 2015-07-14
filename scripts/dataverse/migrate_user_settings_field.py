"""

First run the following in a mongo shell:

    db.getCollection('addondataversenodesettings').update({'user_settings': {'$type': 2}}, {$rename: { user_settings: 'foreign_user_settings'}}, {multi: true})

Then change the user_settings field of AddonDataverseNodeSettings to foreign_user_settings
"""
import sys
import logging

from website.app import init_app
from website.addons.dataverse.model import AddonDataverseNodeSettings
from scripts import utils as script_utils
from modularodm import Q

logger = logging.getLogger('migrate_user_settings_field')

def do_migration(dry=False):
    for dvs in AddonDataverseNodeSettings.find():
        if dvs.foreign_user_settings is None:
            continue
        dvs.user_settings = dvs.foreign_user_settings
        dvs.save()

def main():
    init_app(routes=False)  # Sets the storage backends on all models
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    do_migration(dry)


if __name__ == '__main__':
    main()
