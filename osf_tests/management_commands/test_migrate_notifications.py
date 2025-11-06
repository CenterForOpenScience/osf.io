import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

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
    populate_notification_types, EVENT_NAME_TO_NOTIFICATION_TYPE
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

    ALL_PROVIDER_EVENTS = [
        'new_pending_withdraw_requests',
        'contributor_added_preprint',
        'new_pending_submissions',
        'moderator_added',
        'reviews_submission_confirmation',
        'reviews_resubmission_confirmation',
        'confirm_email_moderation',
    ]

    ALL_NODE_EVENTS = [
        'file_updated',
    ]

    ALL_COLLECTION_EVENTS = [
        'collection_submission_submitted',
        'collection_submission_accepted',
        'collection_submission_rejected',
        'collection_submission_removed_admin',
        'collection_submission_removed_moderator',
        'collection_submission_removed_private',
        'collection_submission_cancel',
    ]

    ALL_EVENT_NAMES = ALL_PROVIDER_EVENTS + ALL_NODE_EVENTS + ALL_COLLECTION_EVENTS

    def create_legacy_sub(self, event_name, users=None, user=None, provider=None, node=None):
        return NotificationSubscriptionLegacy.objects.create(
            _id=f'{(provider or node or user)._id}_{event_name}',
            user=user,
            event_name=event_name,
            provider=provider,
            node=node
        )

    def test_migrate_provider_subscription(self, users, provider, provider2):
        self.create_legacy_sub(event_name='new_pending_submissions', users=users, provider=provider)
        self.create_legacy_sub(event_name='new_pending_submissions', users=users, provider=provider2)
        self.create_legacy_sub(event_name='new_pending_submissions', users=users, provider=RegistrationProvider.get_default())
        migrate_legacy_notification_subscriptions()
        subs = NotificationSubscription.objects.filter(
            notification_type__name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS
        )
        assert subs.count() == 3
        for obj in [provider, provider2, RegistrationProvider.get_default()]:
            content_type = ContentType.objects.get_for_model(obj.__class__)
            assert subs.filter(object_id=obj.id, content_type=content_type).exists()

    def test_migrate_node_subscription(self, users, user, node):
        migrate_legacy_notification_subscriptions()
        nt = NotificationType.objects.get(name=NotificationType.Type.NODE_FILE_UPDATED)
        assert nt.object_content_type == ContentType.objects.get_for_model(Node)
        subs = NotificationSubscription.objects.filter(notification_type=nt)
        assert subs.count() == 1
        for sub in subs:
            assert sub.subscribed_object == node

    def test_multiple_subscriptions_no_old_types(self, users, user, provider, node):
        assert not NotificationSubscription.objects.filter(user=user)
        self.create_legacy_sub('comments', users, user=user, node=node)
        migrate_legacy_notification_subscriptions()
        assert not NotificationSubscription.objects.filter(user=user)

    def test_idempotent_migration(self, users, user, node, provider):
        self.create_legacy_sub('file_updated', users, user=user, node=node)
        migrate_legacy_notification_subscriptions()
        migrate_legacy_notification_subscriptions()
        assert NotificationSubscription.objects.get(
            user=user,
            object_id=node.id,
            content_type=ContentType.objects.get_for_model(node.__class__),
            notification_type__name=NotificationType.Type.NODE_FILE_UPDATED
        )

    def test_migrate_all_subscription_types(self, users, user, provider, provider2, node):
        providers = [provider, provider2]
        for event_name in self.ALL_EVENT_NAMES:
            if event_name in self.ALL_PROVIDER_EVENTS:
                self.create_legacy_sub(event_name=event_name, users=users, user=user, node=node, provider=provider)
                self.create_legacy_sub(event_name=event_name, users=users, user=user, node=node, provider=provider2)
            else:
                self.create_legacy_sub(event_name=event_name, users=users, user=user, node=node)

        # Run migration the first time
        migrate_legacy_notification_subscriptions()
        subs = NotificationSubscription.objects.all()
        # Calculate expected total
        expected_total = len(self.ALL_PROVIDER_EVENTS) * len(providers) \
                         + len(self.ALL_NODE_EVENTS) \
                         + len(self.ALL_COLLECTION_EVENTS)
        assert subs.count() >= expected_total
        # Run migration again to test deduplication
        migrate_legacy_notification_subscriptions()
        subs_after_second_run = NotificationSubscription.objects.all()
        assert subs_after_second_run.count() == subs.count()
        # Verify every notification type is present
        for nt_legacy_name in self.ALL_EVENT_NAMES:
            nt_name = EVENT_NAME_TO_NOTIFICATION_TYPE[nt_legacy_name].value
            nt_objs = NotificationSubscription.objects.filter(
                notification_type__name=nt_name
            )
            assert nt_objs.exists()
        # Verify subscriptions belong to correct objects
        for provider in providers:
            content_type = ContentType.objects.get_for_model(provider.__class__)
            assert NotificationSubscription.objects.filter(
                notification_type=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.instance,
                content_type=content_type,
                object_id=provider.id
            ).exists()
        node_ct = ContentType.objects.get_for_model(node.__class__)
        assert NotificationSubscription.objects.filter(
            notification_type=NotificationType.Type.NODE_FILE_UPDATED.instance,
            content_type=node_ct,
            object_id=node.id
        ).exists()

    def test_migrate_rolls_back_on_runtime_error(self, users, user, node, provider):
        user = AuthUserFactory()
        self.create_legacy_sub(event_name='collection_submission_submitted', users=users, user=user, node=node, provider=provider)

        def failing_migration():
            with transaction.atomic():
                migrate_legacy_notification_subscriptions()
                raise RuntimeError('Simulated failure')

        with pytest.raises(RuntimeError):
            failing_migration()
        assert NotificationSubscription.objects.filter(user=user).count() == 0

    def test_migrate_skips_invalid_data(self, users, user, node, provider):
        self.create_legacy_sub(event_name='wrong_data', users=users, user=user, node=node, provider=provider)
        migrate_legacy_notification_subscriptions()
        assert NotificationSubscription.objects.filter(user=user).count() == 0

    def test_migrate_batch_with_valid_and_invalid(self, users, user, node, provider):
        # Valid subscription
        self.create_legacy_sub(
            event_name='reviews_resubmission_confirmation',
            users=users,
            user=user,
            node=node,
            provider=provider,
        )
        # Invalid subscription
        self.create_legacy_sub(
            event_name='wrong_data',
            users=users,
            user=user,
            node=node,
            provider=provider,
        )
        migrate_legacy_notification_subscriptions()
        assert NotificationSubscription.objects.filter(user=user).count() == 1
        migrated = NotificationSubscription.objects.filter(user=user).first()
        assert migrated.notification_type.name == NotificationType.Type.PROVIDER_REVIEWS_RESUBMISSION_CONFIRMATION.value

    def test_migrate_subscription_frequencies_none(self, user):
        # Create a legacy subscription with all three frequency types
        legacy = self.create_legacy_sub(
            event_name='global_file_updated',
            user=user,
        )
        legacy.none.add(user)

        # Run the migration
        migrate_legacy_notification_subscriptions()

        # Fetch the migrated NotificationType and corresponding subscriptions
        nt = NotificationType.objects.get(name=NotificationType.Type.USER_FILE_UPDATED)
        subs = NotificationSubscription.objects.filter(
            notification_type=nt,
        )
        assert subs.count() == 1
        assert subs.get().message_frequency == 'none'

    def test_migrate_subscription_frequencies_transactional(self, user):
        # Create a legacy subscription with all three frequency types
        legacy = self.create_legacy_sub(
            event_name='global_file_updated',
            user=user,
        )
        legacy.email_transactional.add(user)

        # Run the migration
        migrate_legacy_notification_subscriptions()

        # Fetch the migrated NotificationType and corresponding subscriptions
        nt = NotificationType.objects.get(name=NotificationType.Type.USER_FILE_UPDATED)
        subs = NotificationSubscription.objects.filter(
            notification_type=nt,
            content_type=ContentType.objects.get_for_model(user.__class__),
            object_id=user.id,
        )
        assert subs.count() == 1
        assert subs.get().message_frequency == 'instant'

    def test_migrate_subscription_frequencies_daily(self, user):
        # Create a legacy subscription with all three frequency types

        legacy = self.create_legacy_sub(
            event_name='global_file_updated',
            user=user,
        )
        legacy.email_digest.add(user)

        # Run the migration
        migrate_legacy_notification_subscriptions()

        # Fetch the migrated NotificationType and corresponding subscriptions
        nt = NotificationType.objects.get(name=NotificationType.Type.USER_FILE_UPDATED)
        subs = NotificationSubscription.objects.filter(
            notification_type=nt,
            content_type=ContentType.objects.get_for_model(user.__class__),
            object_id=user.id,
        )
        assert subs.count() == 1
        assert subs.get().message_frequency == 'daily'
