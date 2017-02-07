# -*- coding: utf-8 -*-
"""Migrates GoogleDrive files that have unescaped paths and have a counterpart StoredFileNode. This repoints
the Guid for the unescaped StoredFileNode to the corrct StoredFileNode.

This is a one-off script, run as a prerequisite to scripts.migration.migrate_googledoc_paths.
"""
import sys
import logging

from website.app import init_app
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.models import Guid, StoredFileNode

logger = logging.getLogger(__name__)


targets = [
    {'guid': 'zcjr2', 'good': u'56a42d8f594d900182308a09', 'bad': '56a7cfc49ad5a1017af77922'},
    {'guid': 'nv3xr', 'good': u'57347795594d9000492aaa9a', 'bad': '5734e7d99ad5a101fa57ce7d'},
    {'guid': 'm5nxj', 'good': u'58089970594d9001f1622e35', 'bad': '58452885594d900046bac4db'},
]

def migrate():
    for target in targets:
        guid = Guid.load(target['guid'])
        good_sfn = StoredFileNode.load(target['good'])
        bad_sfn = StoredFileNode.load(target['bad'])

        logger.info('Repointing Guid {} referent to StoredFileNode {}'.format(target['guid'], target['good']))
        guid.referent = good_sfn
        guid.save()

        logger.info('Removing StoredFileNode {}'.format(target['bad']))
        StoredFileNode.remove_one(bad_sfn)


def main():
    dry = '--dry' in sys.argv
    init_app(set_backends=True, routes=False)
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        migrate()
        if dry:
            raise RuntimeError('Dry Run -- Transaction rolled back')


if __name__ == '__main__':
    main()
