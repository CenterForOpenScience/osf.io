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
def subscribe(auth):
    user = auth.user
    subscription = request.json
    event = subscription.get('event')
    notification_type = subscription.get('notification_type')

    node_lineage = []
    if event == 'comment_replies':
        category = user._id
    else:
        category = subscription.get('id')
        node_lineage = get_node_lineage(Node.load(category), [])
        node_lineage.reverse()

    event_id = category + "_" + event

    if notification_type == 'adopt_parent':
        try:
            s = Subscription.find_one(Q('_id', 'eq', event_id))
        except NoResultsFound:
            s = None

        if s:
            for n in settings.NOTIFICATION_TYPES:
                if user in getattr(s, n):
                    getattr(s, n).remove(user)
                    s.save()

    else:
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

        for nt in settings.NOTIFICATION_TYPES:
            if nt != notification_type:
                if user in getattr(s, nt):
                    getattr(s, nt).remove(user)
                    s.save()
