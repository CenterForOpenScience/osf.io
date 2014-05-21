# -*- coding: utf-8 -*-

from flask import request

from modularodm.storedobject import StoredObject

from .concurrency import with_proxies, proxied_members


# ``FlaskStoredObject`` should work when outside a request context, so we use
# a dummy key in this case. Because we can't create weak references to some
# types (str, NoneType, etc.), use an object as the dummy key.
class DummyRequest(object):
    pass
dummy_request = DummyRequest()


def get_flask_key():
    """Get the current Flask request; if not working in request context,
    return the dummy request.

    """
    try:
        return request._get_current_object()
    except RuntimeError:
        return dummy_request


@with_proxies(proxied_members, get_flask_key)
class FlaskStoredObject(StoredObject):
    pass
