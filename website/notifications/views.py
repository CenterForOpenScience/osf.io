import httplib as http
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from model import Subscription
from flask import request
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from modularodm.storage.mongostorage import KeyExistsException
from website.notifications.constants import NOTIFICATION_TYPES
from website.notifications import utils

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

        for nt in NOTIFICATION_TYPES:
            if nt != notification_type:
                if getattr(s, nt) and user in getattr(s, nt):
                    getattr(s, nt).remove(user)
                    s.save()

        return {'message': 'Successfully added ' + repr(user) + ' to ' + notification_type + ' list on ' + event_id}, 200
