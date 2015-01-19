from framework.auth.decorators import must_be_logged_in
from model import Subscription
from flask import request
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from modularodm.storage.mongostorage import KeyExistsException


@must_be_logged_in
def subscribe(auth, **kwargs):
    user = auth.user
    pid = kwargs.get('pid')
    nid = kwargs.get('nid')
    subscriptions = request.json

    for event in subscriptions:
        if event == 'comment_replies':
            category = user._id
        else:
            category = nid if nid else pid

        event_id = category + "_" + event

        # Create subscription or find existing
        for notification_type in subscriptions[event]:
            if subscriptions[event][notification_type]:
                try:
                    s = Subscription(_id=event_id)
                    s.object_id = category
                    s.event_name = event
                    s.save()

                except KeyExistsException:
                    s = Subscription.find_one(Q('_id', 'eq', event_id))
                    s.object_id = category
                    s.event_name = event
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