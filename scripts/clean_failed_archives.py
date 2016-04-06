# -*- coding: utf-8 -*-
"""One-off script to clear out a few registrations that failed during archiving."""
import logging
import sys

from framework.transactions.context import TokuTransaction
from website.app import init_app
from website.archiver import ARCHIVER_FAILURE, ARCHIVER_INITIATED
from website.archiver.model import ArchiveJob

from scripts import utils as script_utils

logger = logging.getLogger(__name__)

FAILED_ARCHIVE_JOBS = [
    '56a8d29e9ad5a10179f77bd6',
]

def clean(reg, dry):
    logger.info('Cleaning registration: {}'.format(reg))
    if not reg.registered_from:
        logger.info('Node {0} had registered_from == None'.format(reg._id))
        return
    if not reg.archive_job:  # Be extra sure not to delete legacy registrations
        logger.info('Skipping legacy registration: {0}'.format(reg._id))
        return
    if not dry:
        reg.archive_job.status = ARCHIVER_FAILURE
        reg.archive_job.sent = True
        reg.archive_job.save()
        reg.root.sanction.forcibly_reject()
        reg.root.sanction.save()
        reg.root.delete_registration_tree(save=True)
    logger.info('Done.')

def main(dry):
    if dry:
        logger.info('[DRY MODE]')
    init_app(routes=False)
    for _id in FAILED_ARCHIVE_JOBS:
        archive_job = ArchiveJob.load(_id)
        assert archive_job.status == ARCHIVER_INITIATED
        root_node = archive_job.dst_node.root
        with TokuTransaction():
            clean(reg=root_node, dry=dry)

if __name__ == "__main__":
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
