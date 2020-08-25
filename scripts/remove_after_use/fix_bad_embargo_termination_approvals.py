import logging
import sys

from website.app import setup_django
setup_django()

from django.db import transaction
from osf.models import EmbargoTerminationApproval
from osf.models import Sanction
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from scripts import utils as scripts_utils


def main(dry=True):
    """
    Fetches embargo termation approvals that were not marked as approved during the cron job.

    The approve_embargo_termination script ran (and 48 hours had passed and there were users that hadn't approved)
    The registrations attached to EmbargoTerminationApprovals were marked as public, and their embargo.state as `completed`,
    but the corresponding embargo_termination_approval was left as `unapproved`.
    """
    bad_state_embargo_termination_approvals = EmbargoTerminationApproval.objects.filter(
        embargoed_registration__is_public=True,
        embargoed_registration__embargo__state=Sanction.COMPLETED,
        state=Sanction.UNAPPROVED
    )
    logging.info('{} EmbargoTerminationApprovals that are going to be marked as approved'.format(bad_state_embargo_termination_approvals.count()))
    logging.info('Affected Registrations: {}'.format((list(bad_state_embargo_termination_approvals.values_list('embargoed_registration__guids___id', flat=True).distinct()))))

    with transaction.atomic():
        bad_state_embargo_termination_approvals.update(state=Sanction.APPROVED)
        logging.info('Bad State EmbargoTerminationApprovals have been approved')

        if dry:
            raise RuntimeError('Dry mode -- rolling back transaction')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry=dry)
