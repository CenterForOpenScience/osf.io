from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import OuterRef, Exists, Q

from osf.models import NotificationSubscription, NotificationType


class Command(BaseCommand):
    help = (
        'Remove duplicate NotificationSubscription records, keeping only the highest-id record: '
        'Default uniqueness: (user, content_type, object_id, notification_type, is_digest); '
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry',
            action='store_true',
            help='Show how many rows would be deleted without deleting anything.',
        )

    def handle(self, *args, **options):

        self.stdout.write('Finding duplicate NotificationSubscription records…')
        digest_type_names = {
            # User types
            NotificationType.Type.USER_NO_ADDON.value,
            # File types
            NotificationType.Type.ADDON_FILE_COPIED.value,
            NotificationType.Type.ADDON_FILE_MOVED.value,
            NotificationType.Type.ADDON_FILE_RENAMED.value,
            NotificationType.Type.FILE_ADDED.value,
            NotificationType.Type.FILE_REMOVED.value,
            NotificationType.Type.FILE_UPDATED.value,
            NotificationType.Type.FOLDER_CREATED.value,
            NotificationType.Type.NODE_FILE_UPDATED.value,
            NotificationType.Type.USER_FILE_UPDATED.value,
            # Review types
            NotificationType.Type.COLLECTION_SUBMISSION_SUBMITTED.value,
            NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.value,
            NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS.value,
            NotificationType.Type.REVIEWS_SUBMISSION_STATUS.value,
        }

        digest_type_ids = NotificationType.objects.filter(
            name__in=digest_type_names
        ).values_list('id', flat=True)

        invalid_non_digest = NotificationSubscription.objects.filter(
            notification_type_id__in=digest_type_ids,
            _is_digest=False,
        )

        invalid_digest = NotificationSubscription.objects.filter(
            ~Q(notification_type_id__in=digest_type_ids),
            _is_digest=True,
        )

        duplicate_same_kind = NotificationSubscription.objects.filter(
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

        to_remove = (
            invalid_non_digest
            | invalid_digest
            | duplicate_same_kind
        )

        count = to_remove.count()
        self.stdout.write(f"Duplicates to remove: {count}")

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No duplicates found.'))
            return

        if options['dry']:
            self.stdout.write(self.style.WARNING('Dry run enabled — no records were deleted.'))
            return

        with transaction.atomic():
            deleted, _ = to_remove.delete()
        self.stdout.write(self.style.SUCCESS(f"Successfully removed {deleted} duplicate records."))
