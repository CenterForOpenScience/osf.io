#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to migrate nodes with invalid categories."""

import sys
import logging

from website.app import init_app
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def do_migration(records, dry=True):
    # ... perform the migration ...

def get_targets():
    # ... return the StoredObjects to migrate ...

def main(dry=True):
    init_app(set_backends=True, routes=False, mfr=False)  # Sets the storage backends on all models
    do_migration(get_targets(), dry=dry)

if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
