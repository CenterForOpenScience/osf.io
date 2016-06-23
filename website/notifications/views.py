import httplib as http

from flask import request

from framework import sentry
from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from website.notifications import utils
from website.notifications.constants import NOTIFICATION_TYPES
from website.notifications.model import NotificationSubscription
from website.project.decorators import must_be_valid_project
from website.project.model import Node


@must_be_logged_in
def get_subscriptions(auth):
    return utils.format_user_and_project_subscriptions(auth.user)


@must_be_logged_in
@must_be_valid_project
def get_node_subscriptions(auth, **kwargs):
    node = kwargs.get('node') or kwargs['project']
    return utils.format_data(auth.user, [node._id])


@must_be_logged_in
def get_file_subscriptions(auth, **kwargs):
    node_id = request.args.get('node_id')
    path = request.args.get('path')
    provider = request.args.get('provider')
    return utils.format_file_subscription(auth.user, node_id, path, provider)


@must_be_logged_in
def configure_subscription(auth):
    user = auth.user
    json_data = request.get_json()
    target_id = json_data.get('id')
    event = json_data.get('event')
    notification_type = json_data.get('notification_type')
    path = json_data.get('path')
    provider = json_data.get('provider')

    if not event or (notification_type not in NOTIFICATION_TYPES and notification_type != 'adopt_parent'):
        raise HTTPError(http.BAD_REQUEST, data=dict(
            message_long='Must provide an event and notification type for subscription.')
        )

    node = Node.load(target_id)
    if 'file_updated' in event and path is not None and provider is not None:
        wb_path = path.lstrip('/')
        event = wb_path + '_file_updated'
    event_id = utils.to_subscription_key(target_id, event)

    if not node:
        # if target_id is not a node it currently must be the current user
        if not target_id == user._id:
            sentry.log_message(
                '{!r} attempted to subscribe to either a bad '
                'id or non-node non-self id, {}'.format(user, target_id)
            )
            raise HTTPError(http.NOT_FOUND)

        if notification_type == 'adopt_parent':
            sentry.log_message(
                '{!r} attempted to adopt_parent of a none node id, {}'.format(user, target_id)
            )
            raise HTTPError(http.BAD_REQUEST)
        owner = user
    else:
        if not node.has_permission(user, 'read'):
            sentry.log_message('{!r} attempted to subscribe to private node, {}'.format(user, target_id))
            raise HTTPError(http.FORBIDDEN)

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
                    raise HTTPError(http.BAD_REQUEST)

            # If adopt_parent make sure that this subscription is None for the current User
            subscription = NotificationSubscription.load(event_id)
            if not subscription:
                return {}  # We're done here

            subscription.remove_user_from_subscription(user)
            return {}

    subscription = NotificationSubscription.load(event_id)

    if not subscription:
        subscription = NotificationSubscription(_id=event_id, owner=owner, event_name=event)

    if node and node._id not in user.notifications_configured:
        user.notifications_configured[node._id] = True
        user.save()

    subscription.add_user_to_subscription(user, notification_type)

    subscription.save()

    return {'message': 'Successfully subscribed to {} list on {}'.format(notification_type, event_id)}
