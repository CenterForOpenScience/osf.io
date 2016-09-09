# -*- coding: utf-8 -*-

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
    Fetch a request key and user id from either a Django or Flask request. Fall back on a process-global dummy object
    if we are not in either type of request
    """
    # TODO: This is ugly use of exceptions; is there a better way to track whether in a given type of request?
    from framework.sessions import get_session

    try:
        req = request._get_current_object()
        session = get_session()
        user_id = session.data.get('auth_user_id')
        return req, user_id
    except RuntimeError:  # Not in a flask request context
        if getattr(api_globals, 'request', None) is not None:
            req = api_globals.request
            try:
                user_id = req.user._id
            except AttributeError:  # Request comes from Admin Module
                return dummy_request, None
            return req, user_id
        else:  # Not in a Django request
            return dummy_request, None


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
