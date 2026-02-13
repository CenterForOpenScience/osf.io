import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import transaction, connection
from django.utils import timezone

from osf.models import Node, RegistrationProvider
from osf_tests.factories import (
    AuthUserFactory,
    PreprintProviderFactory,
    ProjectFactory,
)
from osf.models import (
    NotificationType,
    NotificationTypeEnum,
    NotificationSubscription,
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
            'email_digest': AuthUserFactory(),
            'email_transactional': AuthUserFactory(),
        }

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def provider2(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def node(self):
        project = ProjectFactory()
        # better simulates legacy node by deleting automatic sub
        NotificationSubscription.objects.filter(
            object_id=project._id,
            content_type=ContentType.objects.get_for_model(project)
        ).delete()
        return project

    ALL_EVENT_NAMES = ['global_reviews', 'global_file_updated', 'file_updated']

    def create_legacy_sub(self, event_name, users=None, user=None, provider=None, node=None):
        """
        Create a NotificationSubscriptionLegacy record and insert relations into
        osf_notificationsubscriptionlegacy_email_digest, _email_transactional, and _none tables.
        """

        now = timezone.now()
        user_id = user.id if user else None
        provider_id = provider.id if provider else None
        node_id = node.id if node else None
        _id = f"u{user_id}_{event_name}" if user else event_name

        with connection.cursor() as cursor:
            # 1. Insert into main table
            cursor.execute("""
                INSERT INTO osf_notificationsubscriptionlegacy
                    (_id, event_name, user_id, provider_id, node_id, created, modified)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, [_id, event_name, user_id, provider_id, node_id, now, now])

            subscription_id = cursor.fetchone()[0]

            # 2. Insert into M2M tables
            for frequency, user in users.items():
                cursor.execute(
                    f"""
                    INSERT INTO osf_notificationsubscriptionlegacy_{frequency} (notificationsubscription_id, osfuser_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    [subscription_id, user.id],
                )

        return subscription_id

    def test_migrate_provider_subscription(self, users, provider, provider2):
        self.create_legacy_sub(event_name='global_reviews', users=users, provider=provider)
        self.create_legacy_sub(event_name='global_reviews', users=users, provider=provider2)
        self.create_legacy_sub(event_name='global_reviews', users=users, provider=RegistrationProvider.get_default())
        migrate_legacy_notification_subscriptions()
        subs = NotificationSubscription.objects.filter(
            notification_type__name=NotificationTypeEnum.REVIEWS_SUBMISSION_STATUS
        )
        assert subs.count() == 9
        for obj in [provider, provider2, RegistrationProvider.get_default()]:
            content_type = ContentType.objects.get_for_model(obj.__class__)
            assert subs.filter(object_id=obj.id, content_type=content_type).exists()

    def test_migrate_node_subscription(self, users, user, node):
        migrate_legacy_notification_subscriptions()
        nt = NotificationType.objects.get(name=NotificationTypeEnum.NODE_FILE_UPDATED)
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
        self.create_legacy_sub('file_updated', users, node=node)
        migrate_legacy_notification_subscriptions()
        migrate_legacy_notification_subscriptions()
        for user in users.values():
            assert NotificationSubscription.objects.get(
                user=user,
                object_id=node.id,
                content_type=ContentType.objects.get_for_model(node.__class__),
                notification_type__name=NotificationTypeEnum.NODE_FILE_UPDATED
            )

    def test_migrate_all_subscription_types(self, users, user, provider, provider2, node):
        self.create_legacy_sub(event_name='global_reviews', users=users, user=user)
        self.create_legacy_sub(event_name='file_updated', users=users, node=node)
        self.create_legacy_sub(event_name='global_file_updated', users=users, user=user)

        # Run migration the first time
        migrate_legacy_notification_subscriptions()
        subs = NotificationSubscription.objects.all()
        # Calculate expected total
        expected_total = 9  # 3 event names x 3 users each
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

        node_ct = ContentType.objects.get_for_model(node.__class__)
        assert NotificationSubscription.objects.filter(
            notification_type=NotificationTypeEnum.NODE_FILE_UPDATED.instance,
            content_type=node_ct,
            object_id=node.id
        ).exists()

    def test_migrate_rolls_back_on_runtime_error(self, users, user, node, provider):
        user = AuthUserFactory()
        self.create_legacy_sub(event_name='global_reviews', users=users, user=user, node=node, provider=provider)

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
            event_name='global_reviews',
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
        assert NotificationSubscription.objects.filter(
            notification_type__name=NotificationTypeEnum.REVIEWS_SUBMISSION_STATUS
        ).count() == 3

    def test_migrate_subscription_frequencies_none(self, user, django_db_blocker):
        # Create a legacy subscription
        self.create_legacy_sub(
            event_name='global_file_updated',
            users={'none': user},
            user=user,
        )

        migrate_legacy_notification_subscriptions()

        nt = NotificationType.objects.get(name=NotificationTypeEnum.USER_FILE_UPDATED)
        subs = NotificationSubscription.objects.filter(notification_type=nt)
        assert subs.count() == 1
        assert subs.get().message_frequency == 'none'

    def test_migrate_subscription_frequencies_transactional(self, user, django_db_blocker):
        self.create_legacy_sub(
            event_name='global_file_updated',
            users={'email_transactional': user},
            user=user,
        )

        migrate_legacy_notification_subscriptions()

        nt = NotificationType.objects.get(name=NotificationTypeEnum.USER_FILE_UPDATED)
        subs = NotificationSubscription.objects.filter(
            notification_type=nt,
            content_type=ContentType.objects.get_for_model(user.__class__),
            object_id=user.id,
        )
        assert subs.count() == 1
        assert subs.get().message_frequency == 'instantly'

    def test_migrate_global_subscription_frequencies_daily(self, user, django_db_blocker):
        self.create_legacy_sub(
            event_name='global_file_updated',
            users={'email_digest': user},
            user=user,
        )

        migrate_legacy_notification_subscriptions()

        nt = NotificationType.objects.get(name=NotificationTypeEnum.USER_FILE_UPDATED)
        subs = NotificationSubscription.objects.filter(
            notification_type=nt,
            content_type=ContentType.objects.get_for_model(user.__class__),
            object_id=user.id,
        )
        assert subs.count() == 1
        assert subs.get().message_frequency == 'daily'

    def test_migrate_node_subscription_frequencies_daily(self, user, node, django_db_blocker):
        self.create_legacy_sub(
            event_name='file_updated',
            users={'email_digest': user},
            node=node
        )

        migrate_legacy_notification_subscriptions()

        nt = NotificationType.objects.get(name=NotificationTypeEnum.NODE_FILE_UPDATED)
        subs = NotificationSubscription.objects.filter(
            user=user,
            notification_type=nt,
            content_type=ContentType.objects.get_for_model(node.__class__),
            object_id=node.id,
        )
        assert subs.count() == 1
        assert subs.get().message_frequency == 'daily'

    def test_node_subscription_copy_group_frequency(self, user, node, django_db_blocker):
        self.create_legacy_sub(
            event_name='file_updated',
            users={'email_digest': user},
            node=node
        )

        migrate_legacy_notification_subscriptions()

        NotificationTypeEnum.FILE_UPDATED.instance.emit(
            user=user,
            subscribed_object=node,
            event_context={
                'user_fullname': user.fullname,
            },
            is_digest=True,
        )

        nt = NotificationSubscription.objects.get(
            user=user,
            notification_type__name=NotificationTypeEnum.FILE_UPDATED,
            content_type=ContentType.objects.get_for_model(node),
            object_id=node.id,
        )
        assert nt.message_frequency == 'daily'

    def test_user_subscription_copy_group_frequency(self, user, node, django_db_blocker):
        self.create_legacy_sub(
            event_name='global_file_updated',
            users={'none': user},
            user=user
        )

        migrate_legacy_notification_subscriptions()

        NotificationTypeEnum.FILE_UPDATED.instance.emit(
            user=user,
            subscribed_object=user,
            event_context={
                'user_fullname': user.fullname,
            },
            is_digest=True,
        )

        nt = NotificationSubscription.objects.get(
            user=user,
            notification_type__name=NotificationTypeEnum.FILE_UPDATED,
            content_type=ContentType.objects.get_for_model(user),
            object_id=user.id,
        )
        assert nt.message_frequency == 'none'

    def test_provider_subscription_copy_group_frequency(self, user, node, provider):
        self.create_legacy_sub(
            event_name='global_reviews',
            users={'none': user},
            user=user
        )

        migrate_legacy_notification_subscriptions()

        NotificationTypeEnum.PROVIDER_NEW_PENDING_SUBMISSIONS.instance.emit(
            user=user,
            subscribed_object=provider,
            event_context={
                'user_fullname': user.fullname,
            },
            is_digest=True,
        )

        nt = NotificationSubscription.objects.get(
            user=user,
            notification_type__name=NotificationTypeEnum.PROVIDER_NEW_PENDING_SUBMISSIONS,
            content_type=ContentType.objects.get_for_model(provider),
            object_id=provider.id,
        )
        assert nt.message_frequency == 'none'
