# Scripts

This folder contains all miscellaneous scripts, clean ups, migrations, daily tasks, etc.


## Note for migrations

You'll want to follow the following template for migrations
It provides basic logging utilities and a dry run mode



```python
import sys
import logging
from website.app import setup_django
from scripts import utils as script_utils
from django.db import transaction

setup_django()
from osf.models import OSFUser, AbstractNode


logger = logging.getLogger(__name__)


# This is where all your migration log will go
def do_migration():
    pass


def main(dry=True):
    # Start a transaction that will be rolled back if any exceptions are un
    with transaction.atomic():
        do_migration()
        if dry:
            # When running in dry mode force the transaction to rollback
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)

    # Allow setting the log level just by appending the level to the command
    if '--debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    elif '--warning' in sys.argv:
        logger.setLevel(logging.WARNING)
    elif '--info' in sys.argv:
        logger.setLevel(logging.INFO)
    elif '--error' in sys.argv:
        logger.setLevel(logging.ERROR)

    # Finally run the migration
    main(dry=dry)
```
