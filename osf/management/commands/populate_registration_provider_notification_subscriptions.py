import logging

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from osf.models import NotificationSubscription, RegistrationProvider

logger = logging.getLogger(__file__)


def populate_registration_provider_notification_subscriptions():
    for provider in RegistrationProvider.objects.all():
        try:
            provider_admins = provider.get_group('admin').user_set.all()
            provider_moderators = provider.get_group('moderator').user_set.all()
        except Group.DoesNotExist:
            logger.warn('Unable to find groups for provider "{}", assuming there are no subscriptions to create.'.format(provider._id))
            continue

        for subscription in provider.DEFAULT_SUBSCRIPTIONS:
            instance, created = NotificationSubscription.objects.get_or_create(
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


class Command(BaseCommand):
    help = """
    Creates NotificationSubscriptions for existing RegistrationProvider objects
    and adds RegistrationProvider moderators/admins to subscriptions
     """

    # Management command handler
    def handle(self, *args, **options):
        populate_registration_provider_notification_subscriptions()
