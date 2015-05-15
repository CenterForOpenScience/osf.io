"""Run nightly, this script will activate any pending embargoes that have
elapsed the pending approval time and make public and registrations whose
embargo end dates have been passed.
"""

import datetime
import logging
import sys

from modularodm import Q

from website import models, settings
from website.app import init_app
from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    pending_embargoes = models.Embargo.find(Q('state', 'eq', 'unapproved'))
    for embargo in pending_embargoes:
        if should_be_embargoed(embargo):
            if dry_run:
                logger.warn('Dry run mode')
            parent_registration = models.Node.find_one(Q('embargo', 'eq', embargo))
            logger.warn(
                'Embargo {0} approved. Activating embargo for registration {1}'
                .format(embargo._id, parent_registration._id)
            )
            if not dry_run:
                embargo.state = 'active'
                embargo.save()

    active_embargoes = models.Embargo.find(Q('state', 'eq', 'active'))
    for embargo in active_embargoes:
        if embargo.end_date < datetime.datetime.utcnow():
            parent_registration = models.Node.find_one(Q('embargo', 'eq', embargo))
            if dry_run:
                logger.warn('Dry run mode')
            parent_registration = models.Node.find_one(Q('embargo', 'eq', embargo))
            logger.warn(
                'Embargo {0} complete. Making registration {1} public'
                .format(embargo._id, parent_registration._id)
            )
            if not dry_run:
                parent_registration.set_privacy('public')
                embargo.state = 'completed'
                embargo.save()


def should_be_embargoed(embargo):
    """Returns true if embargo was initiated more than 48 hours prior."""
    return (datetime.datetime.utcnow() - embargo.initiation_date) >= settings.EMBARGO_PENDING_TIME


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    init_app(routes=False, mfr=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)
