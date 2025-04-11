import pytest
from django.contrib.contenttypes.models import ContentType

from osf.models import Node
from osf_tests.factories import (
    AuthUserFactory,
    PreprintProviderFactory,
    ProjectFactory
)
from osf.models.notification import NotificationType, NotificationSubscription
from osf.models.notifications import NotificationSubscriptionLegacy
from osf.management.commands.migrate_notifications import migrate_legacy_notification_subscriptions

@pytest.mark.django_db
class TestNotificationSubscriptionMigration:

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

    def test_migrate_provider_subscription(self, users, user, provider, provider2):
        self.create_legacy_sub(f'{provider.id}_comment_replies', users, user=user, provider=provider)
        self.create_legacy_sub(f'{provider2.id}_comment_replies', users, user=user, provider=provider2)

        migrate_legacy_notification_subscriptions()

        subs = NotificationSubscription.objects.all()
        assert subs.count() == 2
        assert subs.get(
            notification_type__name='comment_replies',
            object_id=provider.id,
            content_type=ContentType.objects.get_for_model(provider.__class__)
        )
        assert subs.get(
            notification_type__name='comment_replies',
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
        self.create_legacy_sub('comment_replies', users, user=user, provider=provider)
        self.create_legacy_sub('wiki_updated', users, user=user, node=node)

        migrate_legacy_notification_subscriptions()

        assert NotificationSubscription.objects.count() == 4

    def test_idempotent_migration(self, users, user, provider):
        self.create_legacy_sub('comment_replies', users, user=user, provider=provider)
        migrate_legacy_notification_subscriptions()
        migrate_legacy_notification_subscriptions()

        assert NotificationSubscription.objects.all().count() == 1
        assert NotificationSubscription.objects.get(notification_type__name='comment_replies')

    def test_skips_invalid_subscription(self, users):
        # Create a legacy subscription with no node or provider
        legacy = NotificationSubscriptionLegacy.objects.create(
            _id='broken',
            event_name='invalid_event'
        )
        legacy.none.add(users['none'])

        migrate_legacy_notification_subscriptions()

        # It should skip, not crash
        assert NotificationType.objects.filter(name='invalid_event').count() == 0
        assert NotificationSubscription.objects.count() == 0
