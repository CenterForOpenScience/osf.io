""" A script for testing DraftRegistrationApprovals. Automatically approves all pending
DraftRegistrationApprovals.
"""
import sys
import logging

from framework.tasks.handlers import celery_teardown_request

from website.app import init_app
from website.project.model import DraftRegistration, Sanction

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARN)
logging.disable(level=logging.INFO)


def main(dry_run=True):
    if dry_run:
        logger.warn('DRY RUN mode')
    pending_approval_drafts = DraftRegistration.find()
    need_approval_drafts = [draft for draft in pending_approval_drafts
                            if draft.approval and draft.requires_approval and draft.approval.state == Sanction.UNAPPROVED]

    for draft in need_approval_drafts:
        sanction = draft.approval
        try:
            if not dry_run:
                sanction.state = Sanction.APPROVED
                sanction._on_complete(None)
                sanction.save()
            logger.warn('Approved {0}'.format(draft._id))
        except Exception as e:
            logger.error(e)

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    app = init_app(routes=False)
    main(dry_run=dry_run)
    celery_teardown_request()
