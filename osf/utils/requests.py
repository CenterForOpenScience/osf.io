# -*- coding: utf-8 -*-
from django.db import transaction
from flask import Request as FlaskRequest
from flask import request
from rest_framework.permissions import SAFE_METHODS
from api.base.api_globals import api_globals
from api.base import settings


class DummyRequest(object):
    pass
dummy_request = DummyRequest()


def check_select_for_update(request=None):
    if not settings.SELECT_FOR_UPDATE_ENABLED:
        return False
    atomic_transaction = transaction.get_connection().in_atomic_block
    if request:
        return request.method not in SAFE_METHODS and atomic_transaction
    return atomic_transaction


def get_current_request():
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

    req = get_current_request()
    user_id = None
    if isinstance(req, FlaskRequest):
        session = get_session()
        user_id = session.data.get('auth_user_id')
    elif hasattr(req, 'user'):
        # admin module can return a user w/o an id
        user_id = getattr(req.user, '_id', None)
    return req, user_id
