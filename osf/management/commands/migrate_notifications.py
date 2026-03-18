import logging
import time
import signal
from contextlib import contextmanager

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection

from osf.models import NotificationType, NotificationTypeEnum, NotificationSubscription
from osf.models.notifications import NotificationSubscriptionLegacy
from osf.management.commands.populate_notification_types import populate_notification_types
from tqdm import tqdm

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 36000  # 10 hours timeout
BATCH_SIZE = 10000       # Default batch size

FREQ_MAP = {
    'none': 'none',
    'email_digest': 'daily',
    'email_transactional': 'instantly',
}

EVENT_NAME_TO_NOTIFICATION_TYPE = {
    # Provider notifications
    'global_reviews': NotificationTypeEnum.REVIEWS_SUBMISSION_STATUS,

    # Node notifications
    'file_updated': NotificationTypeEnum.NODE_FILE_UPDATED,

    # User notifications
    'global_file_updated': NotificationTypeEnum.USER_FILE_UPDATED,
}


def get_legacy_subscribed_users_and_frequency(legacy):
    none = 'SELECT osfuser_id from osf_notificationsubscriptionlegacy_none where notificationsubscription_id = %s'
    email_digest = 'SELECT osfuser_id from osf_notificationsubscriptionlegacy_email_digest where notificationsubscription_id = %s'
    email_transactional = 'SELECT osfuser_id from osf_notificationsubscriptionlegacy_email_transactional where notificationsubscription_id = %s'
    with connection.cursor() as cursor:
        cursor.execute(none, [legacy.id])
        none_users = [row[0] for row in cursor.fetchall()]

        cursor.execute(email_digest, [legacy.id])
        digest_users = [row[0] for row in cursor.fetchall()]

        cursor.execute(email_transactional, [legacy.id])
        transactional_users = [row[0] for row in cursor.fetchall()]

    return {
        'none': none_users,
        'email_digest': digest_users,
        'email_transactional': transactional_users
    }

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutError('Migration timed out')

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def iter_batches(first_id: int, last_id: int, batch_size: int):
    """Yield [start_id, end_id] ranges for batching."""
    for start in range(first_id, last_id + 1, batch_size):
        yield start, min(start + batch_size - 1, last_id)


def build_existing_keys():
    """Fetch already migrated subscription keys to prevent duplicates."""
    return set(
        (
            user_id,
            content_type_id,
            int(object_id) if object_id else None,
            notification_type_id,
        )
        for user_id, content_type_id, object_id, notification_type_id in
        NotificationSubscription.objects.values_list(
            'user_id', 'content_type_id', 'object_id', 'notification_type_id'
        )
    )


def migrate_legacy_notification_subscriptions(
    dry_run=False,
    batch_size=BATCH_SIZE,
    start_id=0,
):
    logger.info('Starting legacy notification subscription migration...')

    legacy_qs = NotificationSubscriptionLegacy.objects.filter(id__gte=start_id, event_name__in=EVENT_NAME_TO_NOTIFICATION_TYPE.keys()).order_by('id')
    legacy_qs_ids = legacy_qs.values_list('id', flat=True)
    if legacy_qs_ids.count() != 0:
        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM osf_notificationsubscriptionlegacy_none where notificationsubscription_id IN %s', [tuple(legacy_qs_ids)])
            none_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM osf_notificationsubscriptionlegacy_email_digest where notificationsubscription_id IN %s', [tuple(legacy_qs_ids)])
            digest_count = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM osf_notificationsubscriptionlegacy_email_transactional where notificationsubscription_id IN %s', [tuple(legacy_qs_ids)])
            transactional_count = cursor.fetchone()[0]

        legacy_expanded_total = none_count + digest_count + transactional_count
    else:
        legacy_expanded_total = 0

    if legacy_expanded_total == 0:
        logger.info('No legacy subscriptions to migrate.')
        return
    logger.info(f"Total legacy subscriptions to process: {legacy_expanded_total}")

    notiftype_map = dict(NotificationType.objects.values_list('name', 'id'))
    existing_keys = build_existing_keys()

    created, skipped = 0, 0
    content_type_cache = {}

    first_id, last_id = legacy_qs.first().id, legacy_qs.last().id
    start_time_total = time.time()

    for batch_range in tqdm(list(iter_batches(first_id, last_id, batch_size)), desc='Processing', unit='batch'):
        batch = list(
            NotificationSubscriptionLegacy.objects
            .filter(id__range=batch_range, event_name__in=EVENT_NAME_TO_NOTIFICATION_TYPE.keys())
            .order_by('id')
            .select_related('provider', 'node', 'user')
        )
        if not batch:
            continue

        subscriptions_to_create = []

        for legacy in batch:
            event_name = legacy.event_name
            subscribed_object = legacy.provider or legacy.node or legacy.user
            if not subscribed_object:
                skipped += 1
                continue

            model_class = subscribed_object.__class__
            if model_class not in content_type_cache:
                content_type_cache[model_class] = ContentType.objects.get_for_model(model_class)
            content_type = content_type_cache[model_class]

            notif_enum = EVENT_NAME_TO_NOTIFICATION_TYPE.get(event_name)
            if subscribed_object == legacy.user and event_name == 'global_file_updated':
                notif_enum = NotificationTypeEnum.USER_FILE_UPDATED
            if not notif_enum:
                skipped += 1
                continue

            notification_type_id = notiftype_map.get(notif_enum)
            if not notification_type_id:
                skipped += 1
                continue

            frequency_data = get_legacy_subscribed_users_and_frequency(legacy)

            for frequency_key, value in frequency_data.items():
                for user_id in value:
                    key = (
                        user_id,
                        content_type.id,
                        int(subscribed_object.id),
                        notification_type_id,
                    )
                    if key in existing_keys:
                        skipped += 1
                        continue
                    frequency = FREQ_MAP[frequency_key]
                    if dry_run:
                        created += 1
                    else:
                        subscriptions_to_create.append(NotificationSubscription(
                            notification_type_id=notification_type_id,
                            user_id=user_id,
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

        logger.info(f"Processed batch {batch_range[0]}-{batch_range[1]} (Created: {created}, Skipped: {skipped})")

    elapsed_total = time.time() - start_time_total
    logger.info(
        f"Migration {'(dry-run) ' if dry_run else ''}completed in {elapsed_total:.2f} seconds: "
        f"{created} created, {skipped} skipped."
    )


def run_migration(dry_run: bool, batch_size: int, start_id: int):
    """Main entry point for command and tests."""
    with time_limit(TIMEOUT_SECONDS):
        if not dry_run:
            with transaction.atomic():
                logger.info('Populating notification types...')
                populate_notification_types(None, {})
        migrate_legacy_notification_subscriptions(dry_run=dry_run, batch_size=batch_size, start_id=start_id)


class Command(BaseCommand):
    help = 'Migrate legacy NotificationSubscriptionLegacy objects to new Notification app models.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run migration in dry-run mode (no DB changes will be committed).'
        )

        parser.add_argument(
            '--batch-size',
            type=int,
            default=BATCH_SIZE,
            help=f'Batch size (default: {BATCH_SIZE})'
        )

        parser.add_argument(
            '--start-id',
            type=int,
            default=0,
            help='Start migrating from this ID'
        )

    def handle(self, *args, **options):
        try:
            run_migration(
                dry_run=options['dry_run'],
                batch_size=options['batch_size'],
                start_id=options['start_id'],
            )
        except TimeoutError:
            logger.error('Migration timed out. Rolling back changes.')
            raise CommandError('Migration failed due to timeout')
        except Exception as e:
            logger.exception('Migration failed. Rolling back changes.')
            raise CommandError(str(e))
