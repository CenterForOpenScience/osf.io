import logging
from framework.celery_tasks import app as celery_app
from django.core.management import call_command
from osf.models import Registration

logger = logging.getLogger(__name__)


@celery_app.task(name='scripts.check_manual_restart_approval')
def check_manual_restart_approval(registration_id):
    try:
        try:
            registration = Registration.objects.get(_id=registration_id)
        except Registration.DoesNotExist:
            logger.error(f"Registration {registration_id} not found")
            return f"Registration {registration_id} not found"

        if registration.is_public or registration.is_registration_approved:
            return f"Registration {registration_id} already approved/public"

        if registration.archiving:
            logger.info(f"Registration {registration_id} still archiving, retrying in 10 minutes")
            check_manual_restart_approval.apply_async(
                args=[registration_id],
                countdown=600
            )
            return f"Registration {registration_id} still archiving, scheduled retry"

        logger.info(f"Processing manual restart approval for registration {registration_id}")

        call_command(
            'process_manual_restart_approvals',
            registration_id=registration_id,
            dry_run=False,
            hours_back=24,
            verbosity=1
        )

        return f"Processed manual restart approval check for registration {registration_id}"

    except Exception as e:
        logger.error(f"Error processing manual restart approval for {registration_id}: {e}")
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