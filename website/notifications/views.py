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

@must_be_valid_project
@must_be_logged_in
def get_node_subscriptions(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    return utils.format_data(auth.user, [node._id], [])

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
            s = Subscription.find_one(Q('_id', 'eq', event_id))
        except NoResultsFound:
            return
        if node and node.parent_node and s.object_id in node.parent_node.child_node_subscriptions[user._id]:
            node.parent_node.child_node_subscriptions[user._id].remove(s.object_id)
            node.parent_node.save()
        s.remove_user_from_subscription(user)

    else:
        try:
            s = Subscription(_id=event_id)
            s.save()

        except KeyExistsException:
            s = Subscription.find_one(Q('_id', 'eq', event_id))

        s.object_id = uid
        s.event_name = event
        s.save()

        # Add user to list of subscribers
        if notification_type not in s._fields:
            setattr(s, notification_type, [])
            s.save()

        if user not in getattr(s, notification_type):
            getattr(s, notification_type).append(user)
            s.save()

        for nt in NOTIFICATION_TYPES:
            if nt != notification_type:
                if getattr(s, nt) and user in getattr(s, nt):
                    getattr(s, nt).remove(user)
                    s.save()

        if node and node.parent_node:
            parent = node.parent_node
            if notification_type == 'none' and s.object_id in parent.child_node_subscriptions.get(user._id, None):
                parent.child_node_subscriptions[user._id].remove(s.object_id)
            elif notification_type != 'none' and s.object_id not in parent.child_node_subscriptions.get(user._id, None):
                parent.child_node_subscriptions[user._id].append(s.object_id)
            node.save()

        return {'message': 'Successfully added ' + repr(user) + ' to ' + notification_type + ' list on ' + event_id}, 200
