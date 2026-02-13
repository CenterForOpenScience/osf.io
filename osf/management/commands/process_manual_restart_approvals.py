import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from osf.models import Registration
from osf.models.admin_log_entry import AdminLogEntry, MANUAL_ARCHIVE_RESTART
from website import settings
from scripts.approve_registrations import approve_past_pendings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process registrations that were manually restarted and may need approval'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )
        parser.add_argument(
            '--hours-back',
            type=int,
            default=72,
            help='How many hours back to look for manual restarts (default: 72)',
        )
        parser.add_argument(
            '--registration-id',
            type=str,
            help='Process a specific registration ID only',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hours_back = options['hours_back']
        specific_registration = options.get('registration_id')

        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY RUN mode - no changes will be made'))

        since = timezone.now() - timedelta(hours=hours_back)

        query = AdminLogEntry.objects.filter(
            action_flag=MANUAL_ARCHIVE_RESTART,
            action_time__gte=since
        )

        if specific_registration:
            try:
                reg = Registration.objects.get(_id=specific_registration)
                query = query.filter(object_id=reg.pk)
                self.stdout.write(f"Processing specific registration: {specific_registration}")
            except Registration.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Registration {specific_registration} not found"))
                return

        manual_restart_logs = query.values_list('object_id', flat=True).distinct()

        registrations_to_check = Registration.objects.filter(
            pk__in=manual_restart_logs,
        )

        self.stdout.write(f"Found {registrations_to_check.count()} manually restarted registrations to check")

        approvals_ready = []
        skipped_registrations = []

        for registration in registrations_to_check:
            status = self.should_auto_approve(registration)

            if status == 'ready':
                approval = registration.registration_approval
                if approval:
                    approvals_ready.append(approval)
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Queuing registration {registration._id} for approval")
                    )
            else:
                skipped_registrations.append((registration._id, status))
                self.stdout.write(
                    self.style.WARNING(f"⚠ Skipping registration {registration._id}: {status}")
                )

        if approvals_ready:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"DRY RUN: Would approve {len(approvals_ready)} registrations")
                )
            else:
                try:
                    approve_past_pendings(approvals_ready, dry_run=False)
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Successfully approved {len(approvals_ready)} manually restarted registrations")
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"✗ Error approving registrations: {e}")
                    )
        else:
            self.stdout.write('No registrations ready for approval')

        self.stdout.write(f"Total checked: {registrations_to_check.count()}")
        self.stdout.write(f"Ready for approval: {len(approvals_ready)}")
        self.stdout.write(f"Skipped: {len(skipped_registrations)}")

        if skipped_registrations:
            self.stdout.write('\nSkipped registrations:')
            for reg_id, reason in skipped_registrations:
                self.stdout.write(f"  - {reg_id}: {reason}")

    def should_auto_approve(self, registration):
        if registration.is_public:
            return 'already public'

        if registration.is_registration_approved:
            return 'already approved'

        if registration.archiving:
            return 'still archiving'

        archive_job = registration.archive_job
        if archive_job and hasattr(archive_job, 'status'):
            if archive_job.status not in ['SUCCESS', None]:
                return f'archive status: {archive_job.status}'

        approval = registration.registration_approval
        if not approval:
            return 'no approval object'

        if approval.is_approved:
            return 'approval already approved'

        if approval.is_rejected:
            return 'approval was rejected'

        time_since_initiation = timezone.now() - approval.initiation_date
        if time_since_initiation < settings.REGISTRATION_APPROVAL_TIME:
            remaining = settings.REGISTRATION_APPROVAL_TIME - time_since_initiation
            return f'not ready yet ({remaining} remaining)'

        if registration.is_stuck_registration:
            return 'registration still stuck'

        return 'ready'
