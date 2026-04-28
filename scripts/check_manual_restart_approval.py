import logging
from framework import sentry
from framework.celery_tasks import app as celery_app
from django.core.management import call_command
from django.utils import timezone
from osf.models import Registration
from scripts.approve_registrations import approve_past_pendings

logger = logging.getLogger(__name__)


@celery_app.task(name='scripts.check_manual_restart_approval')
def check_manual_restart_approval(registration_id):
    try:
        registration = Registration.load(registration_id)
        if not registration:
            logger.error(f"Registration {registration_id} not found")
            return f"Registration {registration_id} not found"

        if registration.is_public or registration.is_registration_approved:
            return f"Registration {registration_id} already approved/public"

        approval = registration.registration_approval
        if not approval:
            logger.info(f"Registration {registration_id} has no registration approval object")
            return f"Registration {registration_id} has no registration approval object"

        if approval.is_rejected:
            logger.info(f"Registration {registration_id} approval was rejected")
            return f"Registration {registration_id} approval was rejected"

        if registration.archiving:
            logger.info(f"Registration {registration_id} still archiving, retrying in 10 minutes")
            check_manual_restart_approval.apply_async(
                args=[registration_id],
                countdown=600
            )
            return f"Registration {registration_id} still archiving, scheduled retry"

        if timezone.now() < approval.auto_approve_at:
            logger.info(f"Registration {registration_id} not ready for auto-approval yet")
            return f"Registration {registration_id} not ready for auto-approval yet"

        logger.info(f"Processing manual restart approval for registration {registration_id}")
        approve_past_pendings([approval], dry_run=False)

        return f"Processed manual restart approval check for registration {registration_id}"

    except Exception as e:
        logger.error(f"Error processing manual restart approval for {registration_id}: {e}")
        sentry.log_exception(e)
        raise


@celery_app.task(name='scripts.check_manual_restart_approvals_batch')
def check_manual_restart_approvals_batch(hours_back=24):
    try:
        logger.info(f"Running batch check for manual restart approvals (last {hours_back} hours)")

        call_command(
            'process_manual_restart_approvals',
            dry_run=False,
            hours_back=hours_back,
            verbosity=1
        )

        return f"Completed batch manual restart approval check for last {hours_back} hours"

    except Exception as e:
        logger.error(f"Error in batch manual restart approval check: {e}")
        raise


@celery_app.task(name='scripts.delayed_manual_restart_approval')
def delayed_manual_restart_approval(registration_id, delay_minutes=30):
    logger.info(f"Scheduling delayed manual restart approval check for {registration_id} in {delay_minutes} minutes")

    check_manual_restart_approval.apply_async(
        args=[registration_id],
        countdown=delay_minutes * 60
    )

    return f"Scheduled manual restart approval check for {registration_id} in {delay_minutes} minutes"