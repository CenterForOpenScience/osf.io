# -*- coding: utf-8 -*-
import sys
from datetime import datetime
import logging

from modularodm import Q

from website.archiver import (
    ARCHIVER_UNCAUGHT_ERROR,
    ARCHIVER_SUCCESS,
)
from website.settings import ARCHIVE_TIMEOUT_TIMEDELTA
from website.archiver.utils import handle_archive_fail
from website.app import init_app
from website.project.model import Node

from scripts import utils as script_utils


logger = logging.getLogger(__name__)

def find_failed_registrations():
    expired_if_before = datetime.utcnow() - ARCHIVE_TIMEOUT_TIMEDELTA
    query = (
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', True) &
        Q('registered_date', 'lt', expired_if_before) &
        Q('__backrefs.active.archivejob', 'exists', True)
    )
    return {node.root for node in Node.find(query) if not node.archive_job.sent or node.archive_job.status != ARCHIVER_SUCCESS}

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
