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

    for event in subscriptions:
        event_id = pid + "_" + event

        if subscriptions[event]:
            try:
                s = Subscription(_id=event_id)
                s.event_name = event

                if not s.types:
                    s.types = {}

                if not 'email' in s.types:
                    s.types = {
                        'email': []
                }
                s.types['email'].append(user.username)
                s.save()

            except KeyExistsException:
                s = Subscription.find_one(Q('_id', 'eq', event_id))
                if user.username not in s.types['email']:
                    s.types['email'].append(user.username)
                    s.save()

        else:
            try:
                s = Subscription.find_one(Q('_id', 'eq', event_id))
                s.types['email'].remove(user.username)
                s.save()
            except NoResultsFound:
                pass

    return {}