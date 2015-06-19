# -*- coding: utf-8 -*-
import sys
from datetime import datetime

from modularodm import Q

from website.archiver import (
    ARCHIVER_NETWORK_ERROR,
    ARCHIVER_SUCCESS,
)
from website.settings import ARCHIVE_TIMEOUT_TIMEDELTA
from website.archiver.utils import handle_archive_fail

from website.project.model import Node

def find_failed_registrations():
    expired_if_before = datetime.now() - ARCHIVE_TIMEOUT_TIMEDELTA
    query = (
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', True) &
        Q('registered_date', 'lt', expired_if_before) &
        Q('__backrefs.active.archivejob', 'exists', True)
    )    
    return [node for node in Node.find(query) if node.archive_job.status != ARCHIVER_SUCCESS]

def remove_failed_registrations(dry_run=True):
    failed = find_failed_registrations()
    if not dry_run:
        for f in failed:
            handle_archive_fail(
                ARCHIVER_NETWORK_ERROR,
                f.registered_from,
                f,
                f.creator,
                f.archived_providers
            )

def main():
    flags = ['dry_run']
    args = {arg: True for arg in sys.argv if arg.lstrip('--') in flags}
    remove_failed_registrations(*args)

if __name__ == '__main__':
    main()
