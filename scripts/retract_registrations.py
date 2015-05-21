"""Script for retracting pending retractions that are more than 48 hours old."""

import datetime
import logging
import sys

from modularodm import Q

from framework.auth import Auth
from framework.transactions.context import TokuTransaction
from website import models, settings
from website.app import init_app
from website.project.model import NodeLog
from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    pending_retractions = models.Retraction.find(Q('state', 'eq', models.Retraction.PENDING))
    for retraction in pending_retractions:
        if should_be_retracted(retraction):
            if dry_run:
                logger.warn('Dry run mode')
            parent_registration = models.Node.find_one(Q('retraction', 'eq', retraction))
            logger.warn(
                'Retraction {0} approved. Retracting registration {1}'
                .format(retraction._id, parent_registration._id)
            )
            if not dry_run:
                with TokuTransaction():
                    retraction.state = models.Retraction.RETRACTED
                    parent_registration.add_log(
                        action=NodeLog.RETRACTION_APPROVED,
                        params={
                            'registration_id': parent_registration._id,
                            'retraction_id': parent_registration.retraction._id,
                        },
                        auth=Auth(parent_registration.retraction.initiated_by),
                        log_date=datetime.datetime.utcnow(),
                        save=False,
                    )
                    retraction.save()


def should_be_retracted(retraction):
    """Returns true if retraction was initiated more than 48 hours prior"""
    return (datetime.datetime.utcnow() - retraction.initiation_date) >= settings.RETRACTION_PENDING_TIME


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    init_app(routes=False, mfr=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)
