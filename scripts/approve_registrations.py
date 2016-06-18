"""Run nightly, this script will approve any pending registrations that have
elapsed the pending approval time..
"""

import logging
import datetime

from modularodm import Q

from framework.celery_tasks import app as celery_app
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website import models, settings

from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    pending_RegistrationApprovals = models.RegistrationApproval.find(Q('state', 'eq', models.RegistrationApproval.UNAPPROVED))
    for registration_approval in pending_RegistrationApprovals:
        if should_be_approved(registration_approval):
            if dry_run:
                logger.warn('Dry run mode')
            pending_registration = models.Node.find_one(Q('registration_approval', 'eq', registration_approval))
            logger.warn(
                'RegistrationApproval {0} automatically approved by system. Making registration {1} public.'
                .format(registration_approval._id, pending_registration._id)
            )
            if not dry_run:
                if pending_registration.is_deleted or pending_registration.archiving:
                    # Clean up any registration failures during archiving
                    registration_approval.forcibly_reject()
                    registration_approval.save()
                    continue

                with TokuTransaction():
                    try:
                        # Ensure no `User` is associated with the final approval
                        registration_approval._on_complete(None)
                    except Exception as err:
                        logger.error(
                            'Unexpected error raised when approving registration for '
                            'registration {}. Continuing...'.format(pending_registration))
                        logger.exception(err)


def should_be_approved(pending_registration):
    """Returns true if pending_registration has surpassed its pending time."""
    return (datetime.datetime.utcnow() - pending_registration.initiation_date) >= settings.REGISTRATION_APPROVAL_TIME


@celery_app.task(name='scripts.approve_registrations')
def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)

