import logging
import time
import signal
from contextlib import contextmanager
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from osf.models import NotificationType, NotificationSubscription
from osf.models.notifications import NotificationSubscriptionLegacy
from osf.management.commands.populate_notification_types import populate_notification_types

logger = logging.getLogger(__name__)

FREQ_MAP = {
    'none': 'none',
    'email_digest': 'weekly',
    'email_transactional': 'instantly',
}
EVENT_NAME_TO_NOTIFICATION_TYPE = {
    # Provider notifications
    'new_pending_withdraw_requests': NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS,
    'contributor_added_preprint': NotificationType.Type.PROVIDER_CONTRIBUTOR_ADDED_PREPRINT,
    'new_pending_submissions': NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS,
    'moderator_added': NotificationType.Type.PROVIDER_MODERATOR_ADDED,
    'reviews_submission_confirmation': NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION,
    'reviews_resubmission_confirmation': NotificationType.Type.PROVIDER_REVIEWS_RESUBMISSION_CONFIRMATION,
    'confirm_email_moderation': NotificationType.Type.PROVIDER_CONFIRM_EMAIL_MODERATION,

    # Node notifications
    'file_updated': NotificationType.Type.NODE_FILE_UPDATED,

    # Collection submissions
    'collection_submission_submitted': NotificationType.Type.COLLECTION_SUBMISSION_SUBMITTED,
    'collection_submission_accepted': NotificationType.Type.COLLECTION_SUBMISSION_ACCEPTED,
    'collection_submission_rejected': NotificationType.Type.COLLECTION_SUBMISSION_REJECTED,
    'collection_submission_removed_admin': NotificationType.Type.COLLECTION_SUBMISSION_REMOVED_ADMIN,
    'collection_submission_removed_moderator': NotificationType.Type.COLLECTION_SUBMISSION_REMOVED_MODERATOR,
    'collection_submission_removed_private': NotificationType.Type.COLLECTION_SUBMISSION_REMOVED_PRIVATE,
    'collection_submission_cancel': NotificationType.Type.COLLECTION_SUBMISSION_CANCEL,
}


TIMEOUT_SECONDS = 3600  # 60 minutes timeout
BATCH_SIZE = 1000 # batch size, can be changed


@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutError("Migration timed out")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def migrate_legacy_notification_subscriptions(
    dry_run=False,
    batch_size=1000,
    timeout_per_batch=300,
    default_frequency='none'
):

    logger.info('Starting legacy notification subscription migration...')

    PROVIDER_BASED_LEGACY_NOTIFICATION_TYPES = [
        'new_pending_submissions',
        'new_pending_withdraw_requests',
        'reviews_submission_confirmation',
        'reviews_moderator_submission_confirmation',
        'reviews_reject_confirmation',
        'reviews_accept_confirmation',
        'reviews_resubmission_confirmation',
        'reviews_comment_edited',
        'contributor_added_preprint',
        'confirm_email_moderation',
        'moderator_added',
        'confirm_email_preprints',
        'user_invite_preprint',
    ]
    def timeout_handler(signum, frame):
        raise TimeoutError("Batch processing timed out")

    # Notification type IDs
    notiftype_map = dict(NotificationType.objects.values_list('name', 'id'))

    # Cache existing keys
    existing_keys = set(
        (
            user_id,
            content_type_id,
            int(object_id) if object_id else None,
            notification_type_id,
        )
        for user_id, content_type_id, object_id, notification_type_id in
        NotificationSubscription.objects.all().values_list(
            "user_id", "content_type_id", "object_id", "notification_type_id"
        )
    )

    total = NotificationSubscriptionLegacy.objects.count()
    created = 0
    skipped = 0
    last_id = 0
    start_time_total = time.time()

    while True:
        batch_start_time = time.time()
        # Fetch the next chunk directly from DB
        batch = list(
            NotificationSubscriptionLegacy.objects
            .filter(id__gt=last_id)
            .order_by("id")[:batch_size]
        )
        if not batch:
            break
        subscriptions_to_create = []

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_per_batch)

        try:
            for legacy in batch:
                event_name = legacy.event_name
                if event_name in PROVIDER_BASED_LEGACY_NOTIFICATION_TYPES:
                    subscribed_object = legacy.provider
                    if not subscribed_object:
                        skipped += 1
                        continue
                elif legacy.node:
                    subscribed_object = legacy.node
                elif legacy.user:
                    subscribed_object = legacy.user
                else:
                    skipped += 1
                    continue

                content_type = ContentType.objects.get_for_model(subscribed_object.__class__)
                notif_enum = EVENT_NAME_TO_NOTIFICATION_TYPE.get(event_name)
                if not notif_enum:
                    skipped += 1
                    continue

                notification_type_id = notiftype_map.get(notif_enum)
                if not notification_type_id:
                    skipped += 1
                    continue

                key = (
                    legacy.user_id,
                    content_type.id,
                    int(subscribed_object.id),
                    notification_type_id,
                )
                if key in existing_keys:
                    skipped += 1
                    continue

                frequency = 'weekly' if getattr(legacy, 'email_digest', False) else default_frequency

                if dry_run:
                    created += 1
                else:
                    subscriptions_to_create.append(NotificationSubscription(
                        notification_type_id=notification_type_id,
                        user_id=legacy.user_id,
                        content_type=content_type,
                        object_id=subscribed_object.id,
                        message_frequency=frequency,
                    ))
                    existing_keys.add(key)

            if not dry_run and subscriptions_to_create:
                with transaction.atomic():
                    NotificationSubscription.objects.bulk_create(
                        subscriptions_to_create,
                        ignore_conflicts=True,
                    )
                    created += len(subscriptions_to_create)

            # Logging ETA
            batch_time = time.time() - batch_start_time
            processed = last_id + len(batch)
            rate = processed / (time.time() - start_time_total)
            eta = (total - processed) / rate if rate else 0

            logger.info(
                f"Processed batch {last_id}-{last_id + len(batch)} "
                f"in {batch_time:.2f}s | "
                f"Progress {processed}/{total} ({processed/total:.1%}) | "
                f"ETA ~ {eta/60:.1f} min"
            )

        except TimeoutError:
            logger.error(f"Batch {last_id}-{last_id + len(batch)} timed out, skipping.")
            skipped += len(batch)
        except Exception as e:
            logger.exception(f"Batch {last_id}-{last_id + len(batch)} failed: {e}")
            skipped += len(batch)
        finally:
            signal.alarm(0)
            last_id = batch[-1].id

    elapsed_total = time.time() - start_time_total
    logger.info(
        f"Migration {'(dry-run) ' if dry_run else ''}completed in {elapsed_total:.2f} seconds: "
        f"{created} created, {skipped} skipped."
    )


class Command(BaseCommand):
    help = 'Migrate legacy NotificationSubscriptionLegacy objects to new Notification app models.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run migration in dry-run mode (no DB changes will be committed).'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        try:
            with time_limit(TIMEOUT_SECONDS):
                if not dry_run:
                    with transaction.atomic():
                        logger.info("Populating notification types...")
                        populate_notification_types(args, options)

                with transaction.atomic():
                    migrate_legacy_notification_subscriptions(dry_run=dry_run)

        except TimeoutError:
            logger.error("Migration timed out. Rolling back changes.")
            raise CommandError("Migration failed due to timeout")
        except Exception as e:
            logger.exception("Migration failed. Rolling back changes.")
            raise CommandError(str(e))

