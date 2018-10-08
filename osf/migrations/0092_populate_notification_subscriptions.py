import logging

from django.db import migrations
from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm, get_perms, remove_perm

logger = logging.getLogger(__file__)


class GroupHelper(object):
    """ Helper for managing permission groups for a given provider during migrations.

        The mixed-in functionality from ReviewProviderMixin is unavailable during migrations
    """

    def __init__(self, provider):
        self.provider = provider

    def format_group(self, name):
        from osf.models.mixins import ReviewProviderMixin
        if name not in ReviewProviderMixin.groups:
            raise ValueError('Invalid reviews group: "{}"'.format(name))
        return ReviewProviderMixin.group_format.format(self=self.provider, group=name)

    def get_group(self, name):
        from django.contrib.auth.models import Group
        return Group.objects.get(name=self.format_group(name))

    def update_provider_auth_groups(self):
        from osf.models.mixins import ReviewProviderMixin
        for group_name, group_permissions in ReviewProviderMixin.groups.items():
            group, created = Group.objects.get_or_create(name=self.format_group(group_name))
            to_remove = set(get_perms(group, self.provider)).difference(group_permissions)
            for p in to_remove:
                remove_perm(p, group, self.provider)
            for p in group_permissions:
                assign_perm(p, group, self.provider)

def populate_provider_notification_subscriptions(apps, schema_editor):
    NotificationSubscription = apps.get_model('osf', 'NotificationSubscription')
    PreprintProvider = apps.get_model('osf', 'PreprintProvider')
    for provider in PreprintProvider.objects.all():
        helper = GroupHelper(provider)
        try:
            provider_admins = helper.get_group('admin').user_set.all()
            provider_moderators = helper.get_group('moderator').user_set.all()
        except Group.DoesNotExist:
            logger.warn('Unable to find groups for provider "{}", assuming there are no subscriptions to create.'.format(provider._id))
            continue
        instance, created = NotificationSubscription.objects.get_or_create(_id='{provider_id}_new_pending_submissions'.format(provider_id=provider._id),
                                                                           event_name='new_pending_submissions',
                                                                           provider=provider)
        for user in provider_admins | provider_moderators:
            # add user to subscription list but set their notification to none by default
            instance.add_user_to_subscription(user, 'email_transactional', save=True)

def revert(apps, schema_editor):
    NotificationSubscription = apps.get_model('osf', 'NotificationSubscription')
    # The revert of this migration deletes all NotificationSubscription instances
    NotificationSubscription.objects.filter(provider__isnull=False).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0091_notificationsubscription_provider'),
    ]

    operations = [
        migrations.RunPython(populate_provider_notification_subscriptions, revert),
    ]
