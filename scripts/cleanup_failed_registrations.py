# -*- coding: utf-8 -*-
import sys
from datetime import datetime
import logging

from modularodm import Q

from website.archiver import ARCHIVER_UNCAUGHT_ERROR
from website.settings import ARCHIVE_TIMEOUT_TIMEDELTA
from website.archiver.utils import handle_archive_fail
from website.archiver.model import ArchiveJob

from website.app import init_app

from scripts import utils as script_utils


logger = logging.getLogger(__name__)

def find_failed_registrations():
    expired_if_before = datetime.utcnow() - ARCHIVE_TIMEOUT_TIMEDELTA
    jobs = ArchiveJob.find(
        Q('sent', 'eq', False) &
        Q('datetime_initiated', 'lt', expired_if_before)
    )
    return {node.root for node in [job.dst_node for job in jobs]}

def remove_failed_registrations(dry_run=True):
    init_app(set_backends=True, routes=False)
    failed = find_failed_registrations()
    if not dry_run:
        for f in failed:
            logging.info('Cleaning {}'.format(f))
            handle_archive_fail(
                ARCHIVER_UNCAUGHT_ERROR,
                f.registered_from,
                f,
                f.creator,
                f.archive_job.target_info()
            )
    logging.info('Cleaned {} registrations'.format(len(failed)))

def main():
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    remove_failed_registrations(dry_run=dry)

if __name__ == '__main__':
    main()
