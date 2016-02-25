# -*- coding: utf-8 -*-

import time
import httplib
import functools

from flask import request

from framework.auth import cas
from framework.auth import signing
from framework.flask import redirect
from framework.exceptions import HTTPError

from .core import Auth


def collect_auth(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
        return func(*args, **kwargs)

    return wrapped


def must_be_logged_in(func):
    """Require that user be logged in. Modifies kwargs to include the current
    user.

    """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
        if kwargs['auth'].logged_in:
            return func(*args, **kwargs)
        else:
            return redirect(cas.get_login_url(request.url))

    return wrapped


def must_be_signed(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if request.method in ('GET', 'DELETE'):
            data = request.args
        else:
            data = request.get_json()

        try:
            sig = data['signature']
            payload = signing.unserialize_payload(data['payload'])
            exp_time = payload['time']
        except (KeyError, ValueError):
            raise HTTPError(httplib.BAD_REQUEST, data={
                'message_short': 'Invalid payload',
                'message_long': 'The request payload could not be deserialized.'
            })

        if not signing.default_signer.verify_payload(sig, payload):
            raise HTTPError(httplib.UNAUTHORIZED)

        if time.time() > exp_time:
            raise HTTPError(httplib.BAD_REQUEST, data={
                'message_short': 'Expired',
                'message_long': 'Signature has expired.'
            })

        kwargs['payload'] = payload
        return func(*args, **kwargs)
    return wrapped
