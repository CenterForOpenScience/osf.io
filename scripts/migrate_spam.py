import logging
import sys

from modularodm import Q
from website.app import init_app
from website.project.model import Comment
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def migrate_status(records):
    for record in records:
        if len(record.reports) > 0:
            record.spam_status = Comment.FLAGGED
        else:
            record.spam_status = Comment.UNKNOWN
        record.save()
        logger.info('Migrated spam_status for comment {}'.format(record._id))


def migrate_latest(records):
    for record in records:
        date = None
        for user, report in record.reports.iteritems():
            if date is None:
                date = report.get('date')
            elif date < report.get('date'):
                date = report.get('date')
        record.latest_report = date
        record.save()
        logger.info('Migrated latest_report for comment {}'.format(record._id))


def get_no_status_targets():
    return Comment.find(Q('spam_status', 'eq', None))


def get_no_latest_targets():
    query = (
        Q('latest_report', 'eq', None) &
        Q('spam_status', 'ne', Comment.UNKNOWN) &
        Q('spam_status', 'ne', None)
    )
    return Comment.find(query)


def main():
    dry_run = False
    status = True
    latest = True
    if '--dry' in sys.argv:
        dry_run = True
    if '--no_status' in sys.argv:
        status = False
    if '--no_latest' in sys.argv:
        latest = False
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        if status:
            migrate_status(get_no_status_targets())
        if latest:
            migrate_latest(get_no_latest_targets())
        if dry_run:
            raise Exception('Dry Run -- Aborting Transaction')


if __name__ == '__main__':
    main()
