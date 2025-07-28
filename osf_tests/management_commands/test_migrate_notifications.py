import pytest
from django.contrib.contenttypes.models import ContentType

from osf.models import Node, RegistrationProvider
from osf_tests.factories import (
    AuthUserFactory,
    PreprintProviderFactory,
    ProjectFactory,
)
from osf.models import (
    NotificationType,
    NotificationSubscription,
    NotificationSubscriptionLegacy
)
from osf.management.commands.migrate_notifications import (
    migrate_legacy_notification_subscriptions,
    populate_notification_types
)

@pytest.mark.django_db
class TestNotificationSubscriptionMigration:

    @pytest.fixture(autouse=True)
    def notification_types(self):
        return populate_notification_types()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def users(self):
        return {
            'none': AuthUserFactory(),
            'digest': AuthUserFactory(),
            'transactional': AuthUserFactory(),
        }

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def provider2(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def node(self):
        return ProjectFactory()

    def create_legacy_sub(self, event_name, users, user=None, provider=None, node=None):
        legacy = NotificationSubscriptionLegacy.objects.create(
            _id=f'{(provider or node)._id}_{event_name}',
            user=user,
            event_name=event_name,
            provider=provider,
            node=node
        )
        legacy.none.add(users['none'])
        legacy.email_digest.add(users['digest'])
        legacy.email_transactional.add(users['transactional'])
        return legacy

    def test_migrate_provider_subscription(self, user, provider, provider2):
        NotificationSubscriptionLegacy.objects.get(
            event_name='new_pending_submissions',
            provider=provider
        )
        NotificationSubscriptionLegacy.objects.get(
            event_name='new_pending_submissions',
            provider=provider2
        )
        NotificationSubscriptionLegacy.objects.get(
            event_name='new_pending_submissions',
            provider=RegistrationProvider.get_default()
        )
        migrate_legacy_notification_subscriptions()

        subs = NotificationSubscription.objects.filter(notification_type__name='new_pending_submissions')
        assert subs.count() == 3
        assert subs.get(
            notification_type__name='new_pending_submissions',
            object_id=provider.id,
            content_type=ContentType.objects.get_for_model(provider.__class__)
        )
        assert subs.get(
            notification_type__name='new_pending_submissions',
            object_id=provider2.id,
            content_type=ContentType.objects.get_for_model(provider2.__class__)
        )

    def test_migrate_node_subscription(self, users, user, node):
        self.create_legacy_sub('wiki_updated', users, user=user, node=node)

        migrate_legacy_notification_subscriptions()

        nt = NotificationType.objects.get(name='wiki_updated')
        assert nt.object_content_type == ContentType.objects.get_for_model(Node)

        subs = NotificationSubscription.objects.filter(notification_type=nt)
        assert subs.count() == 1

        for sub in subs:
            assert sub.subscribed_object == node

    def test_multiple_subscriptions_different_types(self, users, user, provider, node):
        assert not NotificationSubscription.objects.filter(user=user)
        self.create_legacy_sub('wiki_updated', users, user=user, node=node)
        migrate_legacy_notification_subscriptions()
        assert NotificationSubscription.objects.get(user=user).notification_type.name == 'wiki_updated'
        assert NotificationSubscription.objects.get(notification_type__name='wiki_updated', user=user)

    def test_idempotent_migration(self, users, user, node, provider):
        self.create_legacy_sub('file_updated', users, user=user, node=node)
        migrate_legacy_notification_subscriptions()
        migrate_legacy_notification_subscriptions()
        assert NotificationSubscription.objects.get(
            user=user,
            object_id=node.id,
            content_type=ContentType.objects.get_for_model(node.__class__),
            notification_type__name='file_updated'
        )

    def test_errors_invalid_subscription(self, users):
        legacy = NotificationSubscriptionLegacy.objects.create(
            _id='broken',
            event_name='invalid_event'
        )
        legacy.none.add(users['none'])

        with pytest.raises(NotImplementedError):
            migrate_legacy_notification_subscriptions()
