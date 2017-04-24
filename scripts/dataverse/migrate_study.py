#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to migrate dataverse projects to accomodate changes in their 4.0 API.
This assumes that the script `migrate_credentials_to_token` has been run.

Changes:
 - Rename node_addon.study to node_addon.dataset
 - Rename node_addon.study_hdl to node_addon.dataset_doi

"""

import sys
import logging
from modularodm import Q

from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

from addons.dataverse.model import AddonDataverseNodeSettings

logger = logging.getLogger(__name__)


def do_migration(records, dry=True):
    for node_addon in records:

        with TokuTransaction():
            logger.info('Record found for dataset {}'.format(node_addon.study_hdl))
            logger.info('renaming fields for to {}'.format(node_addon.study_hdl))

            if not dry:
                node_addon.dataset_doi = node_addon.study_hdl
                node_addon.dataset = node_addon.study

                node_addon.study_hdl = None
                node_addon.study = None

                node_addon.save()


def get_targets():
    return AddonDataverseNodeSettings.find(
        Q('user_settings', 'ne', None) &
        Q('study_hdl', 'ne', None)
    )


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models
    do_migration(get_targets(), dry=dry)


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
