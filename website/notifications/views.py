from framework.auth.decorators import must_be_logged_in
from model import Subscription
from flask import request
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from modularodm.storage.mongostorage import KeyExistsException
from website.notifications.emails import get_node_lineage
from website.models import Node
from website import settings

@must_be_logged_in
def subscribe(auth, **kwargs):
    user = auth.user
    pid = kwargs.get('pid')
    nid = kwargs.get('nid')
    object_id = nid if nid else pid
    subscriptions = request.json
    update_subscription(user, object_id, subscriptions)

@must_be_logged_in
def batch_subscribe(auth):
    subscriptions = request.json
    for key in subscriptions.keys():
        update_subscription(auth.user, key, subscriptions[key])


def update_subscription(user, object_id, subscriptions):
    for event in subscriptions:
        node_lineage = []
        if event == 'comment_replies':
            category = user._id
        else:
            category = object_id
            node_lineage = get_node_lineage(Node.load(category), [])
            node_lineage.reverse()

        event_id = category + "_" + event

        for notification_type in subscriptions[event]:
            # Create subscription or find existing
            if subscriptions[event][notification_type]:
                try:
                    s = Subscription(_id=event_id)
                    s.save()

                except KeyExistsException:
                    s = Subscription.find_one(Q('_id', 'eq', event_id))

                s.object_id = category
                s.event_name = event
                s.node_lineage = node_lineage
                s.save()

                # Add user to list of subscribers
                if notification_type not in s._fields:
                    setattr(s, notification_type, [])
                    s.save()

                if user not in getattr(s, notification_type):
                    getattr(s, notification_type).append(user)
                    s.save()

            else:
                try:
                    s = Subscription.find_one(Q('_id', 'eq', event_id))
                    if user in getattr(s, notification_type):
                        getattr(s, notification_type).remove(user)
                        s.save()
                except NoResultsFound:
                    pass

    return {}
