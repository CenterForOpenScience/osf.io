"""EmbargoTerminationApprovals are the Sanction subclass that allows users
to make Embargoes public before the official end date. Like RegistrationAprpovals
and Embargoes, if an admin fails to approve or reject this request within 48
hours it is approved automagically.


Run nightly, this script will approve any embargo termination
requests for which not all admins have responded within the 48 hour window.
Makes the Embargoed Node and its components public.
"""

import datetime
import logging
import sys

from modularodm import Q

from framework.transactions.context import TokuTransaction
from website import models, settings
from website.app import init_app
from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def get_pending_embargo_termination_requests():
    auto_approve_time = datetime.datetime.now() - settings.EMBARGO_TERMINATION_PENDING_TIME

    return models.EmbargoTerminationApproval.find(
        Q('initiation_date', 'lt', auto_approve_time) &
        Q('state', 'eq', models.EmbargoTerminationApproval.UNAPPROVED)
    )

def main():
    pending_embargo_termination_requests = get_pending_embargo_termination_requests()
    count = 0
    for request in pending_embargo_termination_requests:
        registration = models.Node.find_one(Q('embargo_termination_approval', 'eq', request))
        if not registration.is_embargoed:
            raise RuntimeError("Registration {0} associated with this embargo termination request ({0}) is not embargoed.".format(
                registration._id,
                request._id
            ))
        embargo = registration.embargo
        if not embargo:
            raise RuntimeError("No Embargo associated with this embargo termination request ({0}) on Node: {1}".format(
                request._id,
                registration._id
            ))
        else:
            count += 1
            logger.info("Ending the Embargo ({0}) of Registration ({1}) early. Making the registration and all of its children public now.".format(embargo._id, registration._id))
            request._on_complete()
            registration.reload()
            assert registration.is_embargoed is False
            assert registration.is_public is True
    logger.info("Auto-approved {0} of {1} embargo termination requests".format(count, len(pending_embargo_termination_requests)))
            
if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    init_app(routes=False)
    with TokuTransaction():
        main()
        if dry_run:
            raise RuntimeError("Dry run, rolling back transaction")
