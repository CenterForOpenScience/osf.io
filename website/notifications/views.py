from framework.auth.decorators import must_be_logged_in
from model import Subscription
from flask import request
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from modularodm.storage.mongostorage import KeyExistsException
from website import settings

@must_be_logged_in
def subscribe(auth):
    user = auth.user
    subscription = request.json
    event = subscription.get('event')
    notification_type = subscription.get('notification_type')

    uid = subscription.get('id')
    event_id = uid + "_" + event

    if notification_type == 'adopt_parent':
        try:
            s = Subscription.find_one(Q('_id', 'eq', event_id))
        except NoResultsFound:
            return
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

        for nt in settings.NOTIFICATION_TYPES:
            if nt != notification_type:
                if getattr(s, nt) and user in getattr(s, nt):
                    getattr(s, nt).remove(user)
                    s.save()
