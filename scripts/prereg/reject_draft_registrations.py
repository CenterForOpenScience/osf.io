""" A script for testing DraftRegistrationApprovals. Automatically adds comments to and rejects
pending DraftRegistrationApprovals
"""
import sys
import logging
import datetime as dt

from website.app import init_app
from website.project.model import DraftRegistration, Sanction

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARN)
logging.disable(level=logging.INFO)


def add_comments(draft):
    comment = [{
        'user': {
            'id': 'itsMe',
            'name': 'Mario!'
        },
        'value': 'Ahoy! This is a comment!',
        'lastModified': dt.datetime.utcnow().isoformat()
    }]
    for question_id, value in draft.registration_metadata.iteritems():
        value['comments'] = comment
    draft.save()

def main(dry_run=True):
    if dry_run:
        logger.warn('DRY RUN mode')
    pending_approval_drafts = DraftRegistration.find()
    need_approval_drafts = [draft for draft in pending_approval_drafts
                            if draft.requires_approval and draft.approval and draft.approval.state == Sanction.UNAPPROVED]

    for draft in need_approval_drafts:
        add_comments(draft)
        sanction = draft.approval
        try:
            if not dry_run:
                sanction.forcibly_reject()
                #manually do the on_reject functionality to prevent send_mail problems
                sanction.meta = {}
                sanction.save()
                draft.approval = None
                draft.save()
            logger.warn('Rejected {0}'.format(draft._id))
        except Exception as e:
            logger.error(e)

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    init_app(routes=False)
    main(dry_run=dry_run)
