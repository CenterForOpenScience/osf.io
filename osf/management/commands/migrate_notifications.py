import logging
from django.contrib.contenttypes.models import ContentType
from osf.models.notification import NotificationType, NotificationSubscription
from osf.models.notifications import NotificationSubscriptionLegacy
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

FREQ_MAP = {
    'none': 'none',
    'email_digest': 'weekly',
    'email_transactional': 'instantly',
}

def migrate_legacy_notification_subscriptions():
    """
    Migrate legacy NotificationSubscription data to new notifications app.
    """
    logger.info('Beginning legacy notification subscription migration...')

    PROVIDER_BASED_LEGACY_NOTIFICATION_TYPES = [f'{provider}_comment_replies' for provider in NotificationSubscriptionLegacy.objects.all().values_list('provider', flat=True) if provider]

    for legacy in NotificationSubscriptionLegacy.objects.all():
        event_name = legacy.event_name
        if event_name in PROVIDER_BASED_LEGACY_NOTIFICATION_TYPES:
            subscribed_object = legacy.provider
            event_name = event_name.replace(f'{legacy.provider.id}_', '')
        elif subscribed_object := legacy.node:
            pass
        elif subscribed_object := legacy.user:
            pass
        else:
            raise NotImplementedError(f'Invalid Notification id {event_name}')
        content_type = ContentType.objects.get_for_model(subscribed_object.__class__)
        subscription, _ = NotificationSubscription.objects.update_or_create(
            notification_type=NotificationType.objects.get(name=event_name),
            user=legacy.user,
            content_type=content_type,
            object_id=subscribed_object.id,
            defaults={
                'user_id': legacy.user.id,
                'message_frequency': 'weekly' if legacy.email_digest.exists() else 'none' 'instantly' if legacy.email_transactional.exists() else 'none',
                'content_type': content_type,
                'object_id': subscribed_object.id,
            }
        )
        logger.info(f'Created NotificationType "{event_name}" with content_type {content_type}')

class Command(BaseCommand):
    help = 'Migrate legacy NotificationSubscriptionLegacy objects to new Notification app models.'

    def handle(self, *args, **options):
        with transaction.atomic():
            migrate_legacy_notification_subscriptions()
