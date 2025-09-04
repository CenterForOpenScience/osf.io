import pytest

from osf.models import RegistrationProvider
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
from osf.management.commands.populate_notification_types import populate_notification_types
from osf.management.commands.rollback_notifications import rollback_notification_subscriptions


@pytest.mark.django_db
class TestNotificationSubscriptionRollback:

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
            'weekly': AuthUserFactory(),
            'instantly': AuthUserFactory(),
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

    def create_sub(self, event_name, users, subscribed_object):
        for message_frequency, user in users.items():
            NotificationSubscription.objects.create(
                notification_type=NotificationType.objects.get(name=event_name),
                user=user,
                message_frequency=message_frequency,
                subscribed_object=subscribed_object,
            )

    def test_rollback_provider_subscription(self, users, provider, provider2):
        self.create_sub(event_name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS, users=users, subscribed_object=provider)
        self.create_sub(event_name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS, users=users, subscribed_object=provider2)
        self.create_sub(event_name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS, users=users, subscribed_object=RegistrationProvider.get_default())
        rollback_notification_subscriptions()

        provider_sub = NotificationSubscriptionLegacy.objects.filter(_id=f'{provider._id}_new_pending_submissions')
        assert provider_sub.count() == 1
        assert provider_sub.first().provider == provider
        assert provider_sub.first().email_transactional.count() == 1
        assert provider_sub.first().email_digest.count() == 1
        assert provider_sub.first().none.count() == 1

        provider2_sub = NotificationSubscriptionLegacy.objects.filter(_id=f'{provider2._id}_new_pending_submissions')
        assert provider2_sub.count() == 1
        assert provider2_sub.first().provider == provider2
        assert provider2_sub.first().email_transactional.count() == 1
        assert provider2_sub.first().email_digest.count() == 1
        assert provider2_sub.first().none.count() == 1

        default_provider_sub = NotificationSubscriptionLegacy.objects.filter(_id=f'{RegistrationProvider.get_default()._id}_new_pending_submissions')
        assert default_provider_sub.count() == 1
        assert default_provider_sub.first().provider == RegistrationProvider.get_default()
        assert default_provider_sub.first().email_transactional.count() == 1
        assert default_provider_sub.first().email_digest.count() == 1
        assert default_provider_sub.first().none.count() == 1

    def test_rollback_node_subscription(self, users, node):
        self.create_sub(NotificationType.Type.NODE_FILE_UPDATED, users, subscribed_object=node)
        rollback_notification_subscriptions()
        node_sub = NotificationSubscriptionLegacy.objects.filter(_id=f'{node._id}_file_updated')
        assert node_sub.count() == 1
        assert node_sub.first().node == node
        assert node_sub.first().email_transactional.count() == 1
        assert node_sub.first().email_digest.count() == 1
        assert node_sub.first().none.count() == 1

    def test_multiple_subscriptions_no_old_types(self, users, user, provider, node):
        assert not NotificationSubscription.objects.filter(user=user)
        self.create_sub(NotificationType.Type.NODE_FORK_COMPLETED, users, subscribed_object=node)
        rollback_notification_subscriptions()
        assert not NotificationSubscriptionLegacy.objects.filter(node=node)

    def test_idempotent_migration(self, users, user, node, provider):
        self.create_sub(NotificationType.Type.NODE_FILE_UPDATED, users, subscribed_object=node)
        rollback_notification_subscriptions()
        rollback_notification_subscriptions()
        node_sub = NotificationSubscriptionLegacy.objects.filter(_id=f'{node._id}_file_updated')
        assert node_sub.count() == 1
        assert node_sub.first().node == node
        assert node_sub.first().email_transactional.count() == 1
        assert node_sub.first().email_digest.count() == 1
        assert node_sub.first().none.count() == 1
