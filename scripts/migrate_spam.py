import logging
import sys

from modularodm import Q
from website.app import init_app
from website.project.model import Comment
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def migrate_comment(comment):
    output = 'Comment fine.'
    try:
        temp = comment.spam_status
    except:
        if len(comment.reports) > 0:
            comment.spam_status = Comment.FLAGGED
    if comment.spam_status not in (Comment.FLAGGED, Comment.SPAM,
                                   Comment.UNKNOWN, Comment.HAM):
        comment.spam_status = Comment.UNKNOWN
    try:
        temp = comment.latest_report
    except:
        date = None
        for user, report in comment.reports.iteritems():
            report_date = report.get('date')
            if date is None or report_date > date:
                date = report_date
        comment.latest_report = date
    comment.save()


def migrate_status(records, dry=True):
    pass


def migrate_latest(records, dry=True):
    pass


def get_no_status_targets():
    return [c for c in Comment.find(Q('spam_status', 'eq', None))]


def get_no_latest_targets():
    query = (
        Q('latest_report', 'eq', None) &
        Q('spam_status', 'ne', Comment.UNKNOWN) &
        Q('spam_status', 'ne', None)
    )
    return [c for c in Comment.find(query)]


def main():
    dry_run = False
    status = True
    latest = True
    if '--dry' in sys.argv:
        dry_run = True
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    if '--no_status' in sys.argv:
        status = False
    if '--no_latest' in sys.argv:
        latest = False
    init_app(set_backends=True, routes=False)


if __name__ == '__main__':
    main()
