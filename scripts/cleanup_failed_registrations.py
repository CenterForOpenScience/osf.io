# -*- coding: utf-8 -*-
import sys
import logging
from datetime import datetime

from modularodm import Q
from framework.transactions.context import TokuTransaction

from website.settings import ARCHIVE_TIMEOUT_TIMEDELTA
from website.archiver import ARCHIVER_UNCAUGHT_ERROR, ARCHIVER_FAILURE
from website.archiver.model import ArchiveJob
from website.archiver.utils import handle_archive_fail
from website.archiver.utils import delete_registration_tree

from website.app import init_app

from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def find_failed_registrations():
    expired_if_before = datetime.utcnow() - ARCHIVE_TIMEOUT_TIMEDELTA
    jobs = ArchiveJob.find(
        Q('sent', 'eq', False) &
        Q('datetime_initiated', 'lt', expired_if_before)
    )
    return {node.root for node in [job.dst_node for job in jobs] if node}


def remove_failed_registrations(dry=True):
    count = 0
    failed = find_failed_registrations()
    for f in failed:
        logging.info('Cleaning {}'.format(f))
        if not f.registered_from:
            logging.info('Node {0} had registered_from == None'.format(f._id))
            continue
        if not f.archive_job:  # Be extra sure not to delete legacy registrations
            continue
        f.archive_job.status = ARCHIVER_FAILURE
        f.archive_job.sent = True
        f.archive_job.save()
        if dry:
            # We want to avoid sending emails here, rather we call the delete tree method ourselves for validation.
            delete_registration_tree(f)
        else:
            handle_archive_fail(
                ARCHIVER_UNCAUGHT_ERROR,
                f.registered_from,
                f,
                f.creator,
                f.archive_job.target_info()
            )
        count += 1
    logging.info('Cleaned {} registrations'.format(count))


def main(dry=True):
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        remove_failed_registrations(dry=dry)
        if dry:
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
