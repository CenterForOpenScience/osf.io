"""EmbargoTerminationApprovals are the Sanction subclass that allows users
to make Embargoes public before the official end date. Like RegistrationAprpovals
and Embargoes, if an admin fails to approve or reject this request within 48
hours it is approved automagically.


Run nightly, this script will approve any embargo termination
requests for which not all admins have responded within the 48 hour window.
Makes the Embargoed Node and its components public.
"""
import sys
import logging

import django
from django.utils import timezone
from django.db import transaction
django.setup()

from framework.celery_tasks import app as celery_app

from osf import models
from website import settings
from website.app import init_app

from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def get_pending_embargo_termination_requests():
    auto_approve_time = timezone.now() - settings.EMBARGO_TERMINATION_PENDING_TIME

    return models.EmbargoTerminationApproval.objects.filter(
        initiation_date__lt=auto_approve_time,
        state=models.EmbargoTerminationApproval.UNAPPROVED
    )

def main():
    pending_embargo_termination_requests = get_pending_embargo_termination_requests()
    count = 0
    for request in pending_embargo_termination_requests:
        try:
            registration = models.Registration.objects.get(embargo_termination_approval=request)
        except models.Registration.DoesNotExist:
            logger.error(
                f'EmbargoTerminationApproval {request._id} is not attached to a registration'
            )
            continue
        if not registration.is_embargoed:
            # Embargo previously completed
            logger.warning(
                f'Registration {registration._id} associated with this embargo '
                f'termination request ({request._id}) is not embargoed.'
            )
            registration.embargo_termination_approval = None
            registration.save()
            continue
        embargo = registration.embargo
        if not embargo:
            # Embargo was otherwise disappeared
            logger.warning(
                f'No Embargo associated with this embargo termination request '
                f'({request._id}) on Node: {registration._id}'
            )
            registration.embargo_termination_approval = None
            registration.save()
            continue
        else:
            count += 1
            logger.info(f'Ending the Embargo ({embargo._id}) of Registration ({registration._id}) early. Making the registration and all of its children public now.')
            # Call 'accept' trigger directly. This will terminate the embargo
            # if the registration is unmoderated or push it into the moderation
            # queue if it is part of a moderated registry.
            request.accept()
            registration.reload()
            embargo_termination_state = registration.embargo_termination_approval.approval_stage
            assert registration.embargo_termination_approval.state == models.Sanction.APPROVED
            assert registration.is_embargoed is False
            assert registration.is_public is True

    logger.info(f'Auto-approved {count} of {len(pending_embargo_termination_requests)} embargo termination requests')

@celery_app.task(name='scripts.approve_embargo_terminations')
def run_main(dry_run=True):
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    init_app(routes=False)
    with transaction.atomic():
        main()
        if dry_run:
            raise RuntimeError('Dry run, rolling back transaction')

if __name__ == '__main__':
    run_main(dry_run='--dry' in sys.argv)
