from website.app import setup_django
setup_django()
from osf.models import NotificationSubscription, PreprintProvider
from api.preprint_providers.permissions import GroupHelper


def main():
    for provider in PreprintProvider.objects.all():
        helper = GroupHelper(provider)
        provider_admins = helper.get_group('admin').user_set.all()
        provider_moderators = helper.get_group('moderator').user_set.all()
        instance, created = NotificationSubscription.objects.get_or_create(_id='{provider_id}_preprints_added'.format(provider_id=provider._id),
                                                                           event_name='preprints_added',
                                                                           provider=provider)
        for user in provider_admins | provider_moderators:
            # add user to subscription list but set their notification to none by default
            instance.none.add(user)
        instance.save()

if __name__ == '__main__':
    main()