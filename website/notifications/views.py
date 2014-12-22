from flask import request
from framework.auth.decorators import must_be_logged_in
from model import Subscription


@must_be_logged_in
def subscribe(auth, **kwargs):
    user = auth.user
    pid = kwargs.get('pid')
    subscriptions = 'comment_added'

    for s in subscriptions:
        subscription = Subscription(_id=pid + "_" + s)

        if not subscription.types:
            subscription.types = {}

        if not 'email' in subscription.types:
            subscription.types = {
                'email': [user.username]
            }

        subscription.save()

    return {}