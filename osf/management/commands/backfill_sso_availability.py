from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from osf.models.institution import Institution, SSOAvailability, IntegrationType


class Command(BaseCommand):
    help = 'Backfill sso_availability using fast DB-level updates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show how many rows would be updated without applying changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Build querysets
        qs_no_protocol = Institution.objects.filter(
            delegation_protocol=IntegrationType.NONE.value
        ).exclude(
            sso_availability=SSOAvailability.UNAVAILABLE.value
        )

        qs_inactive_with_protocol = Institution.objects.filter(
            ~Q(delegation_protocol=IntegrationType.NONE.value),
            deactivated__isnull=False
        ).exclude(
            sso_availability=SSOAvailability.HIDDEN.value
        )

        qs_active_with_protocol = Institution.objects.filter(
            ~Q(delegation_protocol=IntegrationType.NONE.value),
            deactivated__isnull=True
        ).exclude(
            sso_availability=SSOAvailability.PUBLIC.value
        )

        count_no_protocol = qs_no_protocol.count()
        count_inactive = qs_inactive_with_protocol.count()
        count_active = qs_active_with_protocol.count()

        total = count_no_protocol + count_inactive + count_active

        self.stdout.write('Planned updates:')
        self.stdout.write(f"  No protocol → UNAVAILABLE: {count_no_protocol}")
        self.stdout.write(f"  Inactive + protocol → HIDDEN: {count_inactive}")
        self.stdout.write(f"  Active + protocol → PUBLIC: {count_active}")
        self.stdout.write(f"  TOTAL: {total}")

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run, no changes applied.'))
            return

        with transaction.atomic():
            updated_no_protocol = qs_no_protocol.update(
                sso_availability=SSOAvailability.UNAVAILABLE.value
            )

            updated_inactive = qs_inactive_with_protocol.update(
                sso_availability=SSOAvailability.HIDDEN.value
            )

            updated_active = qs_active_with_protocol.update(
                sso_availability=SSOAvailability.PUBLIC.value
            )

        self.stdout.write(
            self.style.SUCCESS(
                'Done:\n'
                f"  UNAVAILABLE: {updated_no_protocol}\n"
                f"  HIDDEN: {updated_inactive}\n"
                f"  PUBLIC: {updated_active}\n"
                f"  TOTAL: {updated_no_protocol + updated_inactive + updated_active}"
            )
        )
