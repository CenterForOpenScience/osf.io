import pytest
from framework.auth import Auth
from osf.models import NotificationType, NotificationSubscription
from osf_tests.factories import ProjectFactory, UserFactory
from tests.utils import capture_notifications
from framework.auth import register_unconfirmed

@pytest.mark.django_db
class TestNodeContributorNotificationUniqueness:
    """Ensure only one NotificationSubscription per user/node is created."""

    def test_only_one_subscription_for_registered_user(self):
        """Adding the same registered contributor twice does not duplicate subscriptions."""
        user = UserFactory()
        project = ProjectFactory()
        auth = Auth(project.creator)

        # First addition
        project.add_contributor(
            user,
            auth=auth,
        )
        project.save()

        # Second addition (should be idempotent)
        project.add_contributor(
            user,
            auth=auth,
        )
        project.save()

        subs = NotificationSubscription.objects.filter(
            user=user,
            content_type__model='abstractnode',
            object_id=project.id,
        )
        assert subs.count() == 1, (
            f"Expected exactly one subscription for registered user {user.id}, "
            f"found {subs.count()}"
        )
        sub = subs.first()
        assert sub.notification_type.name == NotificationType.Type.NODE_FILE_UPDATED

        subs = NotificationSubscription.objects.filter(
            user=user,
            content_type__model='osfuser',
            object_id=user.id,
        )
        assert subs.count() == 1, (
            f"Expected exactly one subscription for registered user {user.id}, "
            f"found {subs.count()}"
        )
        sub = subs.first()
        assert sub.notification_type.name == NotificationType.Type.USER_FILE_UPDATED

    def test_only_one_subscription_for_unregistered_user(self):
        """Adding the same unregistered contributor multiple times creates only one subscription."""
        project = ProjectFactory()
        auth = Auth(project.creator)

        name, email = 'Unreg User', f"unreg_{project._id}@example.org"

        # Add the unregistered contributor once
        unreg_user = project.add_unregistered_contributor(
            fullname=name,
            email=email,
            auth=auth,
            existing_user=None
        )
        project.save()

        # Add the same unregistered contributor again
        unreg_user_2 = project.add_unregistered_contributor(
            fullname=name,
            email=email,
            auth=auth,
            existing_user=unreg_user
        )
        project.save()

        # Ensure both returned objects represent the same logical user
        assert unreg_user._id == unreg_user_2._id

        subs = NotificationSubscription.objects.filter(
            user=unreg_user,
            content_type__model='abstractnode',
            object_id=project.id,
        )
        assert subs.count() == 1, (
            f"Expected exactly one subscription for unregistered user {unreg_user.id}, "
            f"found {subs.count()}"
        )
        sub = subs.first()
        assert sub.notification_type.name == NotificationType.Type.NODE_FILE_UPDATED

        subs = NotificationSubscription.objects.filter(
            user=unreg_user,
            content_type__model='osfuser',
            object_id=unreg_user.id,
        )
        assert subs.count() == 1, (
            f"Expected exactly one subscription for unregistered user {unreg_user.id}, "
            f"found {subs.count()}"
        )
        sub = subs.first()
        assert sub.notification_type.name == NotificationType.Type.USER_FILE_UPDATED

    def test_only_one_subscription_for_creator(self):
        """Ensure the project creator only has one NotificationSubscription for their own node."""
        project = ProjectFactory()
        creator = project.creator
        auth = Auth(creator)

        # Saving or re-adding the creator should not create duplicate subscriptions
        project.save()  # initial creation already creates subscriptions
        project.add_contributor(
            creator,
            auth=auth,
        )
        project.save()
        project.add_contributor(
            creator,
            auth=auth,
        )
        project.save()

        subs = NotificationSubscription.objects.filter(
            user=creator,
            content_type__model='abstractnode',
            object_id=project.id,
        )
        assert subs.count() == 1, (
            f"Expected exactly one subscription for creator {creator.id}, "
            f"found {subs.count()}"
        )
        sub = subs.first()
        assert sub.notification_type.name == NotificationType.Type.NODE_FILE_UPDATED

        subs = NotificationSubscription.objects.filter(
            user=creator,
            content_type__model='osfuser',
            object_id=creator.id,
        )
        assert subs.count() == 1, (
            f"Expected exactly one subscription for registered user {creator.id}, "
            f"found {subs.count()}"
        )
        sub = subs.first()
        assert sub.notification_type.name == NotificationType.Type.USER_FILE_UPDATED

    def test_unregistered_contributor_then_registered_user_only_one_subscription(self):
        """When an unregistered contributor later registers, their subscriptions merge correctly."""
        project = ProjectFactory()
        auth = Auth(project.creator)

        name, email = 'Promoted User', f"promoted_{project._id}@example.org"

        # Add an unregistered contributor
        project.add_unregistered_contributor(
            fullname=name,
            email=email,
            auth=auth,
        )
        project.save()

        registered_user = register_unconfirmed(email, 'fake password', name)

        # After registration, ensure adding the new registered user doesn't create duplicates
        project.add_contributor(registered_user, auth=auth)
        project.save()

        # Verify subscriptions (both node and user types) remain unique
        subs_node = NotificationSubscription.objects.filter(
            user=registered_user,
            content_type__model='abstractnode',
            object_id=project.id,
        )
        assert subs_node.count() == 1, (
            f"Expected one NODE_FILE_UPDATED subscription after registration, found {subs_node.count()}"
        )
        assert subs_node.first().notification_type.name == NotificationType.Type.NODE_FILE_UPDATED

        subs_user = NotificationSubscription.objects.filter(
            user=registered_user,
            content_type__model='osfuser',
            object_id=registered_user.id,
        )
        assert subs_user.count() == 1, (
            f"Expected one USER_FILE_UPDATED subscription after registration, found {subs_user.count()}"
        )
        assert subs_user.first().notification_type.name == NotificationType.Type.USER_FILE_UPDATED

    def test_contributor_removed_then_readded_only_one_subscription(self):
        """Removing a contributor and re-adding them should not duplicate subscriptions."""
        project = ProjectFactory()
        user = UserFactory()
        auth = Auth(project.creator)

        # Add contributor
        project.add_contributor(user, auth=auth)
        project.save()

        # Remove contributor
        project.remove_contributor(user, auth=auth)
        project.save()

        # Re-add the same contributor
        project.add_contributor(user, auth=auth)
        project.save()

        subs_node = NotificationSubscription.objects.filter(
            user=user,
            content_type__model='abstractnode',
            object_id=project.id,
        )
        assert subs_node.count() == 1, (
            f"Expected one NODE_FILE_UPDATED subscription after re-adding, found {subs_node.count()}"
        )
        assert subs_node.first().notification_type.name == NotificationType.Type.NODE_FILE_UPDATED

        subs_user = NotificationSubscription.objects.filter(
            user=user,
            content_type__model='osfuser',
            object_id=user.id,
        )
        assert subs_user.count() == 1, (
            f"Expected one USER_FILE_UPDATED subscription after re-adding, found {subs_user.count()}"
        )
        assert subs_user.first().notification_type.name == NotificationType.Type.USER_FILE_UPDATED
