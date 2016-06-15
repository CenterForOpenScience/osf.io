# -*- coding: utf-8 -*-
import sys
from datetime import datetime
import logging

from modularodm import Q

from website.archiver import (
    ARCHIVER_INITIATED
)

from website import (
    mails,
    settings
)

from website.settings import ARCHIVE_TIMEOUT_TIMEDELTA
from website.archiver.model import ArchiveJob

from website.app import init_app

from scripts import utils as script_utils


logger = logging.getLogger(__name__)


def find_failed_registrations():
    expired_if_before = datetime.utcnow() - ARCHIVE_TIMEOUT_TIMEDELTA
    jobs = ArchiveJob.find(
        Q('sent', 'eq', False) &
        Q('datetime_initiated', 'lt', expired_if_before) &
        Q('status', 'eq', ARCHIVER_INITIATED)
    )
    return {node.root for node in [job.dst_node for job in jobs] if node}


def notify_desk_about_failed_registrations(dry_run=True):
    init_app(set_backends=True, routes=False)
    count = 0
    failed = find_failed_registrations()
    if not dry_run:
        for f in failed:
            logging.info('Cleaning {}'.format(f))
            if not f.registered_from:
                logging.info('Node {0} had registered_from == None'.format(f._id))
                continue
            if not f.archive_job:  # Be extra sure not to deal with legacy registrations
                continue

            # Send an email to the OSF Help Desk
            mails.send_mail(
                to_addr=settings.SUPPORT_EMAIL,
                mail=mails.ARCHIVE_REGISTRATION_STUCK_DESK,
                user=f.creator,
                src=f.registered_from,
                archive_job=f.archve_job,
            )

            count += 1
    logging.info('Found {} registrations, notified the OSF Help Desk'.format(count))


def main():
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    notify_desk_about_failed_registrations(dry_run=dry)

if __name__ == '__main__':
    main()
