"""Run nightly, this script will activate any pending embargoes that have
elapsed the pending approval time and make public and registrations whose
embargo end dates have been passed.
"""

import logging

import django
from django.utils import timezone
from django.db import transaction
django.setup()

from framework.celery_tasks import app as celery_app

from website.app import init_app
from website import settings
from osf.models import Embargo, Registration, NodeLog

from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    pending_embargoes = Embargo.objects.filter(state=Embargo.UNAPPROVED)
    for embargo in pending_embargoes:
        if should_be_embargoed(embargo):
            if dry_run:
                logger.warn('Dry run mode')
            try:
                parent_registration = Registration.objects.get(embargo=embargo)
            except Registration.DoesNotExist:
                logger.error(
                    'Embargo {} is not attached to a registration'.format(embargo._id)
                )
                continue
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

                with transaction.atomic():
                    try:
                        embargo.state = Embargo.APPROVED
                        parent_registration.registered_from.add_log(
                            action=NodeLog.EMBARGO_APPROVED,
                            params={
                                'node': parent_registration.registered_from._id,
                                'registration': parent_registration._id,
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

    active_embargoes = Embargo.objects.filter(state=Embargo.APPROVED)
    for embargo in active_embargoes:
        if embargo.end_date < timezone.now() and not embargo.is_deleted:
            if dry_run:
                logger.warn('Dry run mode')
            parent_registration = Registration.objects.get(embargo=embargo)
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

                with transaction.atomic():
                    try:
                        embargo.state = Embargo.COMPLETED
                        # Need to save here for node.is_embargoed to return the correct
                        # value in Node#set_privacy
                        embargo.save()
                        for node in parent_registration.node_and_primary_descendants():
                            node.set_privacy('public', auth=None, save=True)
                        parent_registration.registered_from.add_log(
                            action=NodeLog.EMBARGO_COMPLETED,
                            params={
                                'node': parent_registration.registered_from._id,
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
    return (timezone.now() - embargo.initiation_date) >= settings.EMBARGO_PENDING_TIME and not embargo.is_deleted


@celery_app.task(name='scripts.embargo_registrations')
def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)

if __name__ == "__main__":
    main(False)
