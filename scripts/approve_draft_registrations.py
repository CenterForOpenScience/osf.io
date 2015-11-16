import sys
import logging

from modularodm import Q

from website.app import init_app
from website.models import DraftRegistration, Sanction, User

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARN)
logging.disable(level=logging.INFO)

username = 'not_a_real_email_12345678987654321@not_a_real_domain1234567890.co'

def set_up():
    user = User.create(username=username, fullname='User', password='password')
    user.save()

def clean_up():
    user = User.find_one(Q('username', 'eq', username))
    User.remove_one(user)

def main(dry_run=True):
    if dry_run:
        logger.warn('DRY RUN mode')
    pending_approval_drafts = DraftRegistration.find()
    need_approval_drafts = [draft for draft in pending_approval_drafts
                            if draft.requires_approval and draft.approval and draft.approval.state == Sanction.UNAPPROVED]

    user = User.find_one(Q('username', 'eq', username))

    for draft in need_approval_drafts:
        sanction = draft.approval
        if not dry_run:
            sanction.add_authorizer(user)
        try:
            if not dry_run:
                token = sanction.approval_state[user._id]['approval_token']
                sanction.approve(user, token)
                sanction.save()
            logger.warn('Approved {0}'.format(draft._id))
        except Exception as e:
            logger.error(e)

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    init_app(routes=False)
    set_up()
    main(dry_run=dry_run)
    clean_up()
