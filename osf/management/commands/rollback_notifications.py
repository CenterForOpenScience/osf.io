import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import signal
from contextlib import contextmanager
from osf.models import NotificationSubscription, NotificationSubscriptionLegacy, NotificationType

logger = logging.getLogger(__name__)

# Reverse maps
FREQ_MAP_ROLLBACK = {
    'none': 'none',
    'weekly': 'email_digest',
    'instantly': 'email_transactional',
}

NOTIFICATION_TYPE_TO_EVENT_NAME = {
    # Provider notifications
    NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS: 'new_pending_withdraw_requests',
    NotificationType.Type.PROVIDER_CONTRIBUTOR_ADDED_PREPRINT: 'contributor_added_preprint',
    NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS: 'new_pending_submissions',
    NotificationType.Type.PROVIDER_MODERATOR_ADDED: 'moderator_added',
    NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION: 'reviews_submission_confirmation',
    NotificationType.Type.PROVIDER_REVIEWS_RESUBMISSION_CONFIRMATION: 'reviews_resubmission_confirmation',
    NotificationType.Type.PROVIDER_CONFIRM_EMAIL_MODERATION: 'confirm_email_moderation',

    # Node notifications
    NotificationType.Type.NODE_FILE_UPDATED: 'file_updated',

    # Collection submissions
    NotificationType.Type.COLLECTION_SUBMISSION_SUBMITTED: 'collection_submission_submitted',
    NotificationType.Type.COLLECTION_SUBMISSION_ACCEPTED: 'collection_submission_accepted',
    NotificationType.Type.COLLECTION_SUBMISSION_REJECTED: 'collection_submission_rejected',
    NotificationType.Type.COLLECTION_SUBMISSION_REMOVED_ADMIN: 'collection_submission_removed_admin',
    NotificationType.Type.COLLECTION_SUBMISSION_REMOVED_MODERATOR: 'collection_submission_removed_moderator',
    NotificationType.Type.COLLECTION_SUBMISSION_REMOVED_PRIVATE: 'collection_submission_removed_private',
    NotificationType.Type.COLLECTION_SUBMISSION_CANCEL: 'collection_submission_cancel',
}

TIMEOUT_SECONDS = 60 * 60  # 60 minutes timeout


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

def rollback_notification_subscriptions(dry_run=False):
    migrated = list(NotificationSubscription.objects.select_related('notification_type', 'content_type'))
    if not migrated:
        logger.info('No NotificationSubscription objects found to rollback.')
        return

    recreated_count = 0
    for sub in migrated:
        notif_type_enum = sub.notification_type.name if sub.notification_type else None
        event_name = NOTIFICATION_TYPE_TO_EVENT_NAME.get(notif_type_enum)

        if not event_name:
            logger.warning(f"Skipping rollback for subscription {sub.id}, unmapped notification type {notif_type_enum}")
            continue

        legacy_freq = FREQ_MAP_ROLLBACK.get(sub.message_frequency, 'none')

        content_type = sub.content_type
        model_class = content_type.model_class()
        subscribed_object = model_class.objects.filter(id=sub.object_id).first()

        if not subscribed_object:
            logger.warning(f"Skipping rollback for subscription {sub.id}, missing subscribed object.")
            continue

        legacy_id = f"{sub.subscribed_object._id}_{event_name}"

        if not dry_run:
            obj, created = NotificationSubscriptionLegacy.objects.get_or_create(
                _id=legacy_id,
                event_name=event_name,
                user_id=subscribed_object if content_type.model == 'osfuser' else None,
                node=subscribed_object if content_type.model == 'abstractnode' else None,
                provider=subscribed_object if content_type.model == 'abstractprovider' else None,
            )

            if sub.user:
                if legacy_freq == 'email_digest':
                    obj.email_digest.add(sub.user)
                elif legacy_freq == 'email_transactional':
                    obj.email_transactional.add(sub.user)
                else:
                    obj.none.add(sub.user)

        recreated_count += 1

    if not dry_run:
        logger.info(f"Rollback complete: recreated {recreated_count} legacy entries.")
    else:
        logger.info(f"[Dry Run] Would recreate {recreated_count} NotificationSubscriptionLegacy entries.")


class Command(BaseCommand):
    help = 'Rollback NotificationSubscription objects back into NotificationSubscriptionLegacy.'

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
                with transaction.atomic():
                    rollback_notification_subscriptions(dry_run=dry_run)

        except TimeoutError:
            logger.error('Migration timed out. Rolling back changes.')
            raise CommandError('Migration failed due to timeout')
        except Exception as e:
            logger.exception('Migration failed. Rolling back changes.')
            raise CommandError(str(e))
