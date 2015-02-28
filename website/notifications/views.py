import httplib as http

from flask import request
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from modularodm.storage.mongostorage import KeyExistsException

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError
from website.notifications import utils
from website.notifications.constants import NOTIFICATION_TYPES
from website.notifications.model import Subscription
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
    subscription = request.json
    event = subscription.get('event')
    notification_type = subscription.get('notification_type')

    if not event or not notification_type:
        raise HTTPError(http.BAD_REQUEST, data=dict(
            message_long="Must provide an event and notification type for subscription.")
        )

    uid = subscription.get('id')
    event_id = utils.to_subscription_key(uid, event)

    node = Node.load(uid)
    if node:
        parent = node.parent_node
        if parent:
            if not parent.child_node_subscriptions:
                parent.child_node_subscriptions = {}
                parent.save()
            if not parent.child_node_subscriptions.get(user._id, None):
                parent.child_node_subscriptions[user._id] = []
                parent.save()

    if notification_type == 'adopt_parent':
        try:
            sub = Subscription.find_one(Q('_id', 'eq', event_id))
        except NoResultsFound:
            return

        if node and node.parent_node and sub in node.child_node_subscriptions.get(user._id, []):
            node.parent_node.child_node_subscriptions[user._id].remove(sub.owner._id)
            node.parent_node.save()

        sub.remove_user_from_subscription(user)

    else:
        try:
            sub = Subscription(_id=event_id)
            sub.save()

        except KeyExistsException:
            sub = Subscription.find_one(Q('_id', 'eq', event_id))

        sub.owner = node
        sub.event_name = event
        sub.save()

        # Add user to list of subscribers
        setattr(sub, notification_type, [])
        sub.save()

        if user not in getattr(sub, notification_type):
            getattr(sub, notification_type).append(user)
            sub.save()

        for nt in NOTIFICATION_TYPES:
            if nt != notification_type and user in getattr(sub, nt):
                getattr(sub, nt).remove(user)
                sub.save()

        if node and node.parent_node:
            parent = node.parent_node
            if notification_type == 'none' and sub.owner._id in parent.child_node_subscriptions.get(user._id, None):
                parent.child_node_subscriptions[user._id].remove(sub.owner._id)
            elif notification_type != 'none' and sub.owner._id not in parent.child_node_subscriptions.get(user._id, None):
                parent.child_node_subscriptions[user._id].append(sub.owner._id)
            node.save()

        return {'message': 'Successfully added ' + repr(user) + ' to ' + notification_type + ' list on ' + event_id}, 200
