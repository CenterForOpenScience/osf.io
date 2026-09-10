import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from framework import sentry
from framework.celery_tasks import app as celery_app
from osf.models import Registration, StuckRegistrationReportConfig
from osf.models.notification_type import NotificationTypeEnum

logger = logging.getLogger(__name__)


def send_report(restarted, stuck, dry_run=False):
    """
    send archive report to the emails set via admin's management commands page. Every
    stuck registration is listed, restarted or not
    """
    config = StuckRegistrationReportConfig.load()
    if not stuck:
        logger.info('No stuck registrations to report')
        return
    if not config.report_is_due():
        logger.info('No recipients configured or the next report is not due yet')
        return

    event_context = {
        'restarted_count': restarted,
        'stuck_count': len(stuck),
        'registrations': stuck,
    }
    if dry_run:
        logger.info(f'[DRY-RUN] Would email {config.emails}: {event_context}')
        return

    for address in config.emails:
        NotificationTypeEnum.DESK_ARCHIVE_RESTART_REPORT.instance.emit(
            destination_address=address,
            event_context=event_context,
        )
    config.last_sent = timezone.now()
    config.save()
    logger.info(f'Emailed the stuck registration report to {config.emails}')


@celery_app.task(name='osf.management.commands.restart_stuck_registrations')
def restart_stuck_registrations(dry_run=False):
    """
    These registrations have ArchiveJobs stuck in initial state after the archivation.
    Restarts the registrations that can be restarted safely and emails a report of every registration that
    has not finished archiving.
    """
    from osf.management.commands.force_archive import archive, DEFAULT_PERMISSIBLE_ADDONS
    from scripts.check_manual_restart_approval import delayed_manual_restart_approval
    from scripts.enhanced_stuck_registration_audit import should_auto_retry
    from scripts.stuck_registration_audit import analyze_failed_registration_nodes

    restarted, stuck = 0, []
    for info in analyze_failed_registration_nodes():
        registration = Registration.load(info['registration'])
        if not registration:
            continue
        result = '' if should_auto_retry(info, registration) else 'needs manual intervention'
        if not result and not dry_run:
            try:
                archive(
                    registration,
                    permissible_addons=DEFAULT_PERMISSIBLE_ADDONS,
                    allow_unconfigured=True,
                    skip_collisions=True,
                )
                logger.info(f'Registration {registration._id} was restarted, scheduling approval check')
                delayed_manual_restart_approval.delay(registration._id, delay_minutes=5)
            except Exception as exc:
                logger.exception(f'Could not restart stuck registration {registration._id}')
                sentry.log_exception(exc)
                result = f'restart failed ({exc.__class__.__name__}: {exc})'

        if not result:
            restarted += 1
        logger.info(f'{"[DRY-RUN]" if dry_run else ""} Registration {registration._id}: {result or "restarted"}')
        stuck.append({
            'registration__id': registration._id,
            'url': registration.absolute_url,
            'result': result or 'restarted',
        })

    logger.info(f'{"[DRY-RUN]" if dry_run else ""} {len(stuck)} registrations have not finished archiving, restarted {restarted}')
    send_report(restarted, stuck, dry_run=dry_run)
    return restarted, len(stuck) - restarted


class Command(BaseCommand):
    help = '''
        This script restarts the registrations stuck in archiving and send emails report for the
        ones that have not finished archiving.
    '''

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

    def handle(self, *args, **options):
        restart_stuck_registrations(dry_run=options.get('dry_run', False))
