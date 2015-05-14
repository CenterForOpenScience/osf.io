"""Script for retracting pending retractions that are more than 48 hours old."""

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
    pending_retractions = models.Retraction.find(Q('state', 'eq', models.Retraction.PENDING))
    for retraction in pending_retractions:
        if should_be_retracted(retraction):
            if dry_run:
                logger.warn('Dry run mode')
            logger.warn('Retracting registration {0}'.format(retraction._id))
            if not dry_run:
                retraction.state = models.Retraction.RETRACTED
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
