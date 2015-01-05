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
    subscriptions = request.json
    notification_types = ['email_transactional']

    for notification_type in notification_types:
        for event in subscriptions:
            event_id = pid + "_" + event

            if subscriptions[event]:
                # Create subscription or find existing
                try:
                    s = Subscription(_id=event_id)
                    s.node_id = pid
                    s.event_name = event
                    s.save()

                except KeyExistsException:
                    s = Subscription.find_one(Q('_id', 'eq', event_id))
                    s.node_id = pid
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
                    getattr(s, notification_type).remove(user)
                    s.save()
                except NoResultsFound:
                    pass

    return {}