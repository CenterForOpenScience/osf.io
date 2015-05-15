#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from datetime import datetime

from modularodm import Q
from modularodm.query import QueryGroup

from framework.archiver import ARCHIVER_CHECKING, ARCHIVER_FAILURE, ARCHIVER_PENDING, ARCHIVE_TIMEOUT_TIMEDELTA
from website.project.model import Node
from website import settings

def find_failed_registrations():
    args = ['or'] + [Q('archived_providers.{0}.status'.format(addon), 'in', [ARCHIVER_FAILURE, ARCHIVER_CHECKING, ARCHIVER_PENDING])
                     for addon in settings.ADDONS_ARCHIVABLE]
    pending = QueryGroup(*args)

    expired_if_before = datetime.now() - ARCHIVE_TIMEOUT_TIMEDELTA
    query =(
        Q('is_deleted', 'eq', False) &
        Q('archiving', 'eq', True) &
        Q('registered_date', 'lt', expired_if_before) &
        pending
    )
    return Node.find(query)

def remove_failed_registrations(dry_run=True):
    failed = find_failed_registrations()
    if not dry_run:
        [f.remove_node for f in failed]

def main():
    flags = ['dry_run']
    args = {arg: True for arg in sys.argv if arg.lstrip('--') in flags}
    remove_failed_registrations(*args)

if __name__ == '__main__':
    main()
