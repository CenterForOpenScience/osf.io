from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied

from rest_framework.exceptions import NotFound

from framework import sentry

from osf.models import AbstractNode, OSFUser
from osf.models.notification_type import NotificationType
from osf.models.notification_subscription import NotificationSubscription


def create_missing_notification_from_legacy_id(legacy_id, user):
    """
    `global_file_updated` and `global_reviews` should exist by default for every user, and `<node_id>_files_update`
    should exist by default if user is a contributor of the node. If not found, create them with `none` frequency
    and `_is_digest=True` as default. Raise error if not found, not authorized or permission denied.
    """

    node_ct = ContentType.objects.get_for_model(AbstractNode)
    user_ct = ContentType.objects.get_for_model(OSFUser)

    user_file_updated_nt = NotificationType.Type.USER_FILE_UPDATED.instance
    reviews_submission_status_nt = NotificationType.Type.REVIEWS_SUBMISSION_STATUS.instance
    node_file_updated_nt = NotificationType.Type.NODE_FILE_UPDATED.instance

    node_guid = 'n/a'

    if legacy_id == f'{user._id}_global_file_updated':
        notification_type = user_file_updated_nt
        content_type = user_ct
        object_id = user.id
    elif legacy_id == f'{user._id}_global_reviews':
        notification_type = reviews_submission_status_nt
        content_type = user_ct
        object_id = user.id
    elif legacy_id.endswith('_global_file_updated') or legacy_id.endswith('_global_reviews'):
        # Mismatched request user and subscription user
        sentry.log_message(f'Permission denied: [user={user._id}, legacy_id={legacy_id}]')
        raise PermissionDenied
    # `<node_id>_files_update` should exist by default if user is a contributor of the node.
    # If not found, create them with `none` frequency and `_is_digest=True` as default.
    elif legacy_id.endswith('_files_updated'):
        notification_type = node_file_updated_nt
        content_type = node_ct
        node_guid = legacy_id[:-len('_files_updated')]
        node = AbstractNode.objects.filter(guids___id=node_guid, is_deleted=False, type='osf.node').first()
        if not node:
            # The node in the legacy subscription ID does not exist or is invalid
            sentry.log_message(
                f'Node not found in legacy subscription ID: [user={user._id}, legacy_id={legacy_id}]',
            )
            raise NotFound
        if not node.is_contributor(user):
            # The request user is not a contributor of the node
            sentry.log_message(
                f'Permission denied: [user={user._id}], node={node_guid}, legacy_id={legacy_id}]',
            )
            raise PermissionDenied
        object_id = node.id
    else:
        sentry.log_message(f'Subscription not found: [user={user._id}, legacy_id={legacy_id}]')
        raise NotFound
    missing_subscription_created = NotificationSubscription.objects.create(
        notification_type=notification_type,
        user=user,
        content_type=content_type,
        object_id=object_id,
        _is_digest=True,
        message_frequency='none',
    )
    sentry.log_message(
        f'Missing default subscription has been created: [user={user._id}], node={node_guid} type={notification_type}, legacy_id={legacy_id}]',
    )
    return missing_subscription_created
