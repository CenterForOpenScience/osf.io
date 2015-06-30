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
        try:
            return api_globals.request
        except AttributeError:  # Not in a Django request # TODO: Edge case- are threads re-used across requests?
            return dummy_request


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
