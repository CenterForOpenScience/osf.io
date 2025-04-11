from rest_framework import status as http_status

from flask import request

from framework import sentry
from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from osf.models import AbstractNode, NotificationSubscription, Registration
from osf.utils.permissions import READ


@must_be_logged_in
def configure_subscription(auth):
    user = auth.user
    json_data = request.get_json()
    target_id = json_data.get('id')
    event = json_data.get('event')
    notification_type = json_data.get('notification_type')
    path = json_data.get('path')
    provider = json_data.get('provider')

    NOTIFICATION_TYPES = {
        'none': 'none',
        'instant': 'email_transactional',
        'daily': 'email_digest',
    }

    if not event or (notification_type not in NOTIFICATION_TYPES and notification_type != 'adopt_parent'):
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
            message_long='Must provide an event and notification type for subscription.')
        )

    node = AbstractNode.load(target_id)
    if 'file_updated' in event and path is not None and provider is not None:
        wb_path = path.lstrip('/')
        event = wb_path + '_file_updated'
    event_id = event

    if not node:
        # if target_id is not a node it currently must be the current user
        if not target_id == user._id:
            sentry.log_message(
                '{!r} attempted to subscribe to either a bad '
                'id or non-node non-self id, {}'.format(user, target_id)
            )
            raise HTTPError(http_status.HTTP_404_NOT_FOUND)

        if notification_type == 'adopt_parent':
            sentry.log_message(
                f'{user!r} attempted to adopt_parent of a none node id, {target_id}'
            )
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
        owner = user
    else:
        if not node.has_permission(user, READ):
            sentry.log_message(f'{user!r} attempted to subscribe to private node, {target_id}')
            raise HTTPError(http_status.HTTP_403_FORBIDDEN)

        if isinstance(node, Registration):
            sentry.log_message(
                f'{user!r} attempted to subscribe to registration, {target_id}'
            )
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

        if notification_type != 'adopt_parent':
            owner = node
        else:
            if 'file_updated' in event and len(event) > len('file_updated'):
                pass
            else:
                parent = node.parent_node
                if not parent:
                    sentry.log_message(
                        '{!r} attempted to adopt_parent of '
                        'the parentless project, {!r}'.format(user, node)
                    )
                    raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

            # If adopt_parent make sure that this subscription is None for the current User
            subscription = NotificationSubscription.objects.get(
                notification_type__name=event_id,
                user=user
            )
            subscription.remove_user_from_subscription(user)
            return {}

    subscription = NotificationSubscription.objects.get_or_create(
        notification_type__name=event_id,
        user=owner
    )

    if node and node._id not in user.notifications_configured:
        user.notifications_configured[node._id] = True
        user.save()

    subscription.save()

    return {'message': f'Successfully subscribed to {notification_type} list on {event_id}'}
