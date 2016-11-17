# -*- coding: utf-8 -*-

from flask import Request as FlaskRequest
from flask import request
from modularodm.storedobject import StoredObject as GenericStoredObject
from modularodm.ext.concurrency import with_proxies, proxied_members

from bson import ObjectId
from .handlers import client, database, set_up_storage


from api.base.api_globals import api_globals


class DummyRequest(object):
    pass
dummy_request = DummyRequest()


def get_cache_key():
    """
    Fetch a request key from either a Django or Flask request. Fall back on a process-global dummy object
    if we are not in either type of request
    """
    # TODO: This should be consolidated into framework
    # TODO: This is ugly use of exceptions; is there a better way to track whether in a given type of request?
    try:
        return request._get_current_object()
    except RuntimeError:  # Not in a flask request context
        if getattr(api_globals, 'request', None) is not None:
            return api_globals.request
        else:  # Not in a Django request
            return dummy_request


def get_request_and_user_id():
    """
    Fetch a request and user id from either a Django or Flask request.
    """
    # TODO: This should be consolidated into framework
    from framework.sessions import get_session

    req = get_cache_key()
    user_id = None
    if isinstance(req, FlaskRequest):
        session = get_session()
        user_id = session.data.get('auth_user_id')
    elif hasattr(req, 'user'):
        # admin module can return a user w/o an id
        user_id = getattr(req.user, '_id', None)
    return req, user_id


@with_proxies(proxied_members, get_cache_key)
class StoredObject(GenericStoredObject):
    pass


__all__ = [
    'StoredObject',
    'ObjectId',
    'client',
    'database',
    'set_up_storage',
]
