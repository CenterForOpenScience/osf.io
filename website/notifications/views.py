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
def configure_subscription(auth):
    user = auth.user
    target_id = request.get_json().get('id')
    event = request.get_json().get('event')
    notification_type = request.get_json().get('notification_type')

    if not event or not notification_type:
        raise HTTPError(http.BAD_REQUEST, data=dict(
            message_long="Must provide an event and notification type for subscription.")
        )

    node = Node.load(target_id)
    event_id = utils.to_subscription_key(target_id, event)

    if not node:
        # if target_id is not a node it current must be a user that is the current user
        if not target_id == user._id:
            sentry.log_message('{!r} attempted to subscribe to either a bad id or non-node non-self id, {}', format(user, target_id))
            raise HTTPError(http.BAD_REQUEST)

        if notification_type == 'adopt_parent':
            sentry.log_message('{!r} attempted to adopt_parent of a none node id, {}', format(user, target_id))
            raise HTTPError(http.BAD_REQUEST)
        owner = user

    else:
        if notification_type != 'adopt_parent':
            owner = node
        else:
            parent = node.parent_node
            if not parent:
                sentry.log_message('{!r} attempted to adopt_parent of the parentless project, {!r}'.format(user, node))
                raise HTTPError(http.BAD_REQUEST)

            # If adopt_parent make sure that this subscription is None for the current User
            subscription = NotificationSubscription.load(event_id)
            if not subscription:
                return {}  # We're done here

            # This logic should be moved to the subscription model
            if subscription in node.child_node_subscriptions.get(user._id, []):
                node.parent_node.child_node_subscriptions[user._id].remove(subscription.owner._id)
                node.parent_node.save()

            subscription.remove_user_from_subscription(user)
            return {}

    subscription = NotificationSubscription.load(event_id)

    if not subscription:
        subscription = NotificationSubscription(_id=event_id, owner=owner, event_name=event)
        getattr(subscription, notification_type).append(user)
        subscription.save()
    else:
        # Ensure that user is only recieving the notifications that opted for
        for nt in NOTIFICATION_TYPES:
            if user in getattr(subscription, nt):
                if nt != notification_type:
                    getattr(subscription, nt).remove(user)
            else:
                if nt == notification_type:
                    getattr(subscription, nt).append(user)

        subscription.save()

    return {'message': 'Successfully added ' + repr(user) + ' to ' + notification_type + ' list on ' + event_id}, 200
