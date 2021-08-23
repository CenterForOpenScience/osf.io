"""Run nightly, this script will approve any pending registrations that have
elapsed the pending approval time..
"""
import sys
import logging

import django
from django.utils import timezone
from django.db import transaction
django.setup()

from framework.celery_tasks import app as celery_app

from osf import models
from website.app import init_app
from website import settings

from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    approvals_past_pending = models.RegistrationApproval.objects.filter(
        state=models.RegistrationApproval.UNAPPROVED,
        initiation_date__lt=timezone.now() - settings.REGISTRATION_APPROVAL_TIME
    )

    for registration_approval in approvals_past_pending:
        if dry_run:
            logger.warn('Dry run mode')
        try:
            pending_registration = models.Registration.objects.get(registration_approval=registration_approval)
        except models.Registration.DoesNotExist:
            logger.error(
                'RegistrationApproval {} is not attached to a registration'.format(registration_approval._id)
            )
            continue
        logger.warn(
            'RegistrationApproval {0} automatically approved by system. Making registration {1} public.'
            .format(registration_approval._id, pending_registration._id)
        )
        if not dry_run:
            if pending_registration.is_deleted:
                # Clean up any registration failures during archiving
                registration_approval.forcibly_reject()
                registration_approval.save()
                continue
            if pending_registration.archiving:
                continue

            with transaction.atomic():
                try:
                    # Call 'accept' trigger directly. This will terminate the embargo
                    # if the registration is unmoderated or push it into the moderation
                    # queue if it is part of a moderated registry.
                    registration_approval.accept()
                except Exception as err:
                    logger.error(
                        'Unexpected error raised when approving registration for '
                        'registration {}. Continuing...'.format(pending_registration))
                    logger.exception(err)


@celery_app.task(name='scripts.approve_registrations')
def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)

if __name__ == '__main__':
    run_main(dry_run='--dry' in sys.argv)
