"""Run nightly, this script will activate any pending embargoes that have
elapsed the pending approval time and make public and registrations whose
embargo end dates have been passed.
"""

import logging

import django
from django.utils import timezone
from django.db import transaction
django.setup()

# init_app must be called before sentry is imported
from website.app import init_app
init_app(routes=False)

from framework import sentry
from framework.celery_tasks import app as celery_app

from website import settings
from osf.models import Embargo, Registration

from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    pending_embargoes = Embargo.objects.filter(state=Embargo.UNAPPROVED)
    for embargo in pending_embargoes:
        if should_be_embargoed(embargo):
            if dry_run:
                logger.warning('Dry run mode')
            try:
                parent_registration = Registration.objects.get(embargo=embargo)
            except Registration.DoesNotExist:
                logger.error(
                    f'Embargo {embargo._id} is not attached to a registration'
                )
                continue
            logger.warning(
                'Embargo {} approved. Activating embargo for registration {}'
                .format(embargo._id, parent_registration._id)
            )
            if not dry_run:
                if parent_registration.is_deleted:
                    # Clean up any registration failures during archiving
                    embargo.forcibly_reject()
                    embargo.save()
                    continue

                sid = transaction.savepoint()
                try:
                    # Call 'accept' trigger directly. This will terminate the embargo
                    # if the registration is unmoderated or push it into the moderation
                    # queue if it is part of a moderated registry.
                    embargo.accept()
                    transaction.savepoint_commit(sid)
                except Exception as err:
                    root = parent_registration._dirty_root
                    embargo = root.embargo

                    logger.error(
                        f'Unexpected error raised when activating embargo for '
                        f'registration {parent_registration._id}. Error: {err}',
                        exc_info=err,
                        extra={
                            'is_public': root.is_public,
                            'approval_stage': embargo.approval_stage.name,
                            'is_approved': root.embargo.is_approved
                        }
                    )
                    logger.exception(err)
                    sentry.log_exception(err)

                    transaction.savepoint_rollback(sid)

    active_embargoes = Embargo.objects.filter(state=Embargo.APPROVED)
    for embargo in active_embargoes:
        if True:
            if dry_run:
                logger.warning('Dry run mode')
            parent_registration = Registration.objects.get(embargo=embargo)
            logger.warning(
                'Embargo {} complete. Making registration {} public'
                .format(embargo._id, parent_registration._id)
            )
            if not dry_run:
                if parent_registration.is_deleted:
                    # Clean up any registration failures during archiving
                    embargo.forcibly_reject()
                    embargo.save()
                    continue

                sid = transaction.savepoint()
                try:
                    parent_registration.terminate_embargo()
                    transaction.savepoint_commit(sid)
                except Exception as err:
                    root = parent_registration._dirty_root
                    embargo = root.embargo

                    logger.error(
                        f'Registration {parent_registration._id} could not be made public because {str(err)}',
                        exc_info=err,
                        extra={
                            'is_public': root.is_public,
                            'approval_stage': embargo.approval_stage.name,
                            'is_approved': root.embargo.is_approved
                        }
                    )
                    logger.exception(err)
                    sentry.log_exception(err)

                    transaction.savepoint_rollback(sid)


def should_be_embargoed(embargo):
    """Returns true if embargo was initiated more than 48 hours prior."""
    return (timezone.now() - embargo.initiation_date) >= settings.EMBARGO_PENDING_TIME and not embargo.is_deleted


@celery_app.task(name='scripts.embargo_registrations')
def run_main(dry_run=True):
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)

if __name__ == '__main__':
    main(False)
