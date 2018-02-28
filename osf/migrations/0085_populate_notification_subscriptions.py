import logging

from django.db import migrations

from osf.models import NotificationSubscription, PreprintProvider
from api.preprint_providers.permissions import GroupHelper

logger = logging.getLogger(__file__)

instances_created = []

def populate_provider_notification_subscriptions(*args):
    for provider in PreprintProvider.objects.all():
        helper = GroupHelper(provider)
        provider_admins = helper.get_group('admin').user_set.all()
        provider_moderators = helper.get_group('moderator').user_set.all()
        instance, created = NotificationSubscription.objects.get_or_create(_id='{provider_id}_preprints_added'.format(provider_id=provider._id),
                                                                           event_name='preprints_added',
                                                                           provider=provider)
        if created:
            instances_created.append(instance)
        for user in provider_admins | provider_moderators:
            # add user to subscription list but set their notification to none by default
            instance.none.add(user)
        instance.save()

def revert(*args):
    # The revert of this migration deletes all NotificationSubscription instances
    for instance in instances_created:
        instance.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0084_notificationsubscription_provider'),
    ]

    operations = [
        migrations.RunPython(populate_provider_notification_subscriptions, revert),
    ]
