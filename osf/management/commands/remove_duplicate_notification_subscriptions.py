from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import OuterRef, Exists

from osf.models import NotificationSubscription


class Command(BaseCommand):
    help = (
        'Remove duplicate NotificationSubscription records, keeping only '
        'the highest-id record per (user, content_type, object_id, notification_type).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry',
            action='store_true',
            help='Show how many rows would be deleted without deleting anything.',
        )

    def handle(self, *args, **options):
        self.stdout.write('Finding duplicate NotificationSubscription records…')

        to_remove = NotificationSubscription.objects.filter(
            Exists(
                NotificationSubscription.objects.filter(
                    user_id=OuterRef('user_id'),
                    content_type_id=OuterRef('content_type_id'),
                    object_id=OuterRef('object_id'),
                    notification_type_id=OuterRef('notification_type_id'),
                    _is_digest=OuterRef('_is_digest'),
                    id__gt=OuterRef('id'),  # keep most recent record
                )
            )
        )

        count = to_remove.count()
        self.stdout.write(f"Duplicates to remove: {count}")

        if options['dry']:
            self.stdout.write(
                self.style.WARNING('Dry run enabled — no records were deleted.')
            )
            return

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No duplicates found.'))
            return

        with transaction.atomic():
            deleted, _ = to_remove.delete()

        self.stdout.write(
            self.style.SUCCESS(f"Successfully removed {deleted} duplicate records.")
        )
