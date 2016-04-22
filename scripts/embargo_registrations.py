"""Run nightly, this script will activate any pending embargoes that have
elapsed the pending approval time and make public and registrations whose
embargo end dates have been passed.
"""

import logging
import datetime

from modularodm import Q

from framework.celery_tasks import app as celery_app
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website import models, settings
from website.project.model import NodeLog

from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    pending_embargoes = models.Embargo.find(Q('state', 'eq', models.Embargo.UNAPPROVED))
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
                if parent_registration.is_deleted:
                    # Clean up any registration failures during archiving
                    embargo.forcibly_reject()
                    embargo.save()
                    continue

                with TokuTransaction():
                    try:
                        embargo.state = models.Embargo.APPROVED
                        parent_registration.registered_from.add_log(
                            action=NodeLog.EMBARGO_APPROVED,
                            params={
                                'node': parent_registration._id,
                                'embargo_id': embargo._id,
                            },
                            auth=None,
                        )
                        embargo.save()
                    except Exception as err:
                        logger.error(
                            'Unexpected error raised when activating embargo for '
                            'registration {}. Continuing...'.format(parent_registration))
                        logger.exception(err)

    active_embargoes = models.Embargo.find(Q('state', 'eq', models.Embargo.APPROVED))
    for embargo in active_embargoes:
        if embargo.end_date < datetime.datetime.utcnow():
            if dry_run:
                logger.warn('Dry run mode')
            parent_registration = models.Node.find_one(Q('embargo', 'eq', embargo))
            logger.warn(
                'Embargo {0} complete. Making registration {1} public'
                .format(embargo._id, parent_registration._id)
            )
            if not dry_run:
                if parent_registration.is_deleted:
                    # Clean up any registration failures during archiving
                    embargo.forcibly_reject()
                    embargo.save()
                    continue

                with TokuTransaction():
                    try:
                        embargo.state = models.Embargo.COMPLETED
                        for node in parent_registration.node_and_primary_descendants():
                            node.set_privacy('public', auth=None, save=True)
                        parent_registration.registered_from.add_log(
                            action=NodeLog.EMBARGO_COMPLETED,
                            params={
                                'node': parent_registration.registered_from_id,
                                'registration': parent_registration._id,
                                'embargo_id': embargo._id,
                            },
                            auth=None,
                        )
                        embargo.save()
                    except Exception as err:
                        logger.error(
                            'Unexpected error raised when completing embargo for '
                            'registration {}. Continuing...'.format(parent_registration))
                        logger.exception(err)


def should_be_embargoed(embargo):
    """Returns true if embargo was initiated more than 48 hours prior."""
    return (datetime.datetime.utcnow() - embargo.initiation_date) >= settings.EMBARGO_PENDING_TIME


@celery_app.task(name='scripts.embargo_registrations')
def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)
