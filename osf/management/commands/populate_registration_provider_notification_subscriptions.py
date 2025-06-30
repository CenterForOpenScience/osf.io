import logging

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from osf.models import RegistrationProvider, NotificationSubscriptionLegacy, NotificationType

logger = logging.getLogger(__file__)


def populate_registration_provider_notification_subscriptions():
    for provider in RegistrationProvider.objects.all():
        try:
            provider_admins = provider.get_group('admin').user_set.all()
            provider_moderators = provider.get_group('moderator').user_set.all()
        except Group.DoesNotExist:
            logger.warning(f'Unable to find groups for provider "{provider._id}", assuming there are no subscriptions to create.')
            continue

        for subscription in provider.DEFAULT_SUBSCRIPTIONS:
            # Populate NotificationSubscriptionLegacy
            instance, created = NotificationSubscriptionLegacy.objects.get_or_create(
                _id=f'{provider._id}_{subscription}',
                event_name=subscription,
                provider=provider
            )

            if created:
                logger.info(f'{provider._id}_{subscription} NotificationSubscription object has been created')
            else:
                logger.info(f'{provider._id}_{subscription}  NotificationSubscription object exists')

            for user in provider_admins | provider_moderators:
                # add user to subscription list but set their notification to none by default
                instance.add_user_to_subscription(user, 'email_transactional', save=True)
                logger.info(f'User {user._id} is subscribed to {provider._id}_{subscription}')

            # Populate NotificationSubscription
            subscription_type = NotificationType.objects.filter(name=subscription)

            if not subscription_type.exists():
                logger.warning(f'NotificationType {subscription} does not exist, skipping subscription creation for provider {provider._id}')
                continue
            subscription_type = subscription_type.first()
            for user in provider_admins | provider_moderators:
                subscription_type.add_user_to_subscription(user=user, provider=provider)
                logger.info(f'User {user._id} is subscribed to {subscription_type.name} for provider {provider._id}')


class Command(BaseCommand):
    help = """
    Creates NotificationSubscriptions for existing RegistrationProvider objects
    and adds RegistrationProvider moderators/admins to subscriptions
     """

    # Management command handler
    def handle(self, *args, **options):
        populate_registration_provider_notification_subscriptions()
