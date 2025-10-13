import logging

from django.core.management import call_command
from framework.celery_tasks import app as celery_app
from osf.models import Registration
from osf.management.commands.force_archive import archive, DEFAULT_PERMISSIBLE_ADDONS
from scripts.stuck_registration_audit import analyze_failed_registration_nodes

logger = logging.getLogger(__name__)


@celery_app.task(name='scripts.enhanced_stuck_registration_audit')
def enhanced_stuck_registration_audit():
    logger.info('Starting enhanced stuck registration audit')

    try:
        logger.info('Processing pending manual restart approvals')
        call_command('process_manual_restart_approvals', dry_run=False, hours_back=72)
    except Exception as e:
        logger.error(f"Error processing manual restart approvals: {e}")

    logger.info('Analyzing failed registrations')
    failed_registrations = analyze_failed_registration_nodes()

    if not failed_registrations:
        logger.info('No failed registrations found')
        return 'No failed registrations found'

    logger.info(f"Found {len(failed_registrations)} failed registrations")

    auto_retryable = []
    needs_manual_intervention = []

    for reg_info in failed_registrations:
        registration_id = reg_info['registration']

        try:
            registration = Registration.objects.get(_id=registration_id)

            if should_auto_retry(reg_info, registration):
                auto_retryable.append(registration)
                logger.info(f"Registration {registration_id} eligible for auto-retry")
            else:
                needs_manual_intervention.append(reg_info)
                logger.info(f"Registration {registration_id} needs manual intervention")

        except Registration.DoesNotExist:
            logger.warning(f"Registration {registration_id} not found")
            needs_manual_intervention.append(reg_info)
            continue

    successfully_retried = []
    failed_auto_retries = []

    for reg in auto_retryable:
        try:
            logger.info(f"Attempting auto-retry for stuck registration {reg._id}")

            archive(
                reg,
                permissible_addons=DEFAULT_PERMISSIBLE_ADDONS,
                allow_unconfigured=True,
                skip_collisions=True
            )

            successfully_retried.append(reg._id)
            logger.info(f"Successfully auto-retried registration {reg._id}")

        except Exception as e:
            logger.error(f"Auto-retry failed for registration {reg._id}: {e}")
            failed_auto_retries.append({
                'registration': reg._id,
                'auto_retry_error': str(e),
                'original_info': next(info for info in failed_registrations if info['registration'] == reg._id)
            })

    needs_manual_intervention.extend(failed_auto_retries)

    logger.info(f"Auto-retry results: {len(successfully_retried)} successful, {len(failed_auto_retries)} failed")

    summary = {
        'total_failed': len(failed_registrations),
        'auto_retried_success': len(successfully_retried),
        'auto_retried_failed': len(failed_auto_retries),
        'needs_manual': len(needs_manual_intervention),
        'successfully_retried_ids': successfully_retried
    }

    logger.info(f"Enhanced audit completed: {summary}")
    return summary


def should_auto_retry(reg_info, registration):
    if not reg_info.get('can_be_reset', False):
        return False

    addon_list = reg_info.get('addon_list', [])
    complex_addons = set(addon_list) - {'osfstorage', 'wiki'}
    if complex_addons:
        logger.info(f"Registration {registration._id} has complex addons: {complex_addons}")
        return False

    logs_after_reg = reg_info.get('logs_on_original_after_registration_date', [])
    if logs_after_reg:
        logger.info(f"Registration {registration._id} has post-registration logs: {logs_after_reg}")
        return False

    successful_after = reg_info.get('succeeded_registrations_after_failed', [])
    if successful_after:
        logger.info(f"Registration {registration._id} has successful registrations after failure: {successful_after}")
        return False

    import django.utils.timezone as timezone
    from datetime import timedelta
    if registration.registered_date:
        age = timezone.now() - registration.registered_date
        if age > timedelta(days=30):
            logger.info(f"Registration {registration._id} is too old ({age.days} days)")
            return False
    return True

@celery_app.task(name='scripts.manual_restart_approval_batch')
def manual_restart_approval_batch():
    logger.info('Running manual restart approval batch task')

    try:
        from scripts.check_manual_restart_approval import check_manual_restart_approvals_batch
        result = check_manual_restart_approvals_batch.delay(hours_back=24)
        return f"Queued manual restart approval batch task: {result.id}"
    except Exception as e:
        logger.error(f"Error running manual restart approval batch: {e}")
        raise


if __name__ == '__main__':
    result = enhanced_stuck_registration_audit()
    print(f"Audit completed: {result}")