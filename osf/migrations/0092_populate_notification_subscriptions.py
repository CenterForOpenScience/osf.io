import logging

from django.db import migrations
from django.apps import apps

from api.preprint_providers.permissions import GroupHelper

logger = logging.getLogger(__file__)

NotificationSubscription = apps.get_model('osf', 'NotificationSubscription')
PreprintProvider = apps.get_model('osf', 'PreprintProvider')

def populate_provider_notification_subscriptions(*args):
    for provider in PreprintProvider.objects.all():
        helper = GroupHelper(provider)
        provider_admins = helper.get_group('admin').user_set.all()
        provider_moderators = helper.get_group('moderator').user_set.all()
        instance, created = NotificationSubscription.objects.get_or_create(_id='{provider_id}_new_pending_submissions'.format(provider_id=provider._id),
                                                                           event_name='new_pending_submissions',
                                                                           provider=provider)
        for user in provider_admins | provider_moderators:
            # add user to subscription list but set their notification to none by default
            instance.add_user_to_subscription(user, 'email_transactional', save=True)

def revert(*args):
    # The revert of this migration deletes all NotificationSubscription instances
    NotificationSubscription.objects.filter(provider__isnull=False).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0091_notificationsubscription_provider'),
    ]

    operations = [
        migrations.RunPython(populate_provider_notification_subscriptions, revert),
    ]
