# -*- coding: utf-8 -*-

from rest_framework import status as http_status
import logging
from framework.exceptions import HTTPError

from django.db import transaction
from flask import request, current_app, has_request_context, _request_ctx_stack
from werkzeug.local import LocalProxy


LOCK_ERROR_CODE = http_status.HTTP_400_BAD_REQUEST
NO_AUTO_TRANSACTION_ATTR = '_no_auto_transaction'

logger = logging.getLogger(__name__)

def _get_current_atomic():
    if has_request_context():
        ctx = _request_ctx_stack.top
        return getattr(ctx, 'current_atomic', None)
    return None

current_atomic = LocalProxy(_get_current_atomic)

def no_auto_transaction(func):
    setattr(func, NO_AUTO_TRANSACTION_ATTR, True)
    return func


def view_has_annotation(attr):
    try:
        endpoint = request.url_rule.endpoint
    except (RuntimeError, AttributeError):
        return False
    view = current_app.view_functions[endpoint]
    return getattr(view, attr, False)


def transaction_before_request():
    """Setup transaction before handling the request.
    """
    if view_has_annotation(NO_AUTO_TRANSACTION_ATTR):
        return None
    ctx = _request_ctx_stack.top
    atomic = transaction.atomic()
    atomic.__enter__()
    ctx.current_atomic = atomic

def transaction_after_request(response, base_status_code_error=500):
    """Teardown transaction after handling the request. Rollback if an
    uncaught exception occurred, else commit. If the commit fails due to a lock
    error, rollback and return error response.
    """
    if view_has_annotation(NO_AUTO_TRANSACTION_ATTR):
        return response
    if response.status_code >= base_status_code_error:
        # Construct an error in order to trigger rollback in transaction.atomic().__exit__
        exc_type = HTTPError
        exc_value = HTTPError(response.status_code)
        current_atomic.__exit__(exc_type, exc_value, None)
    else:
        current_atomic.__exit__(None, None, None)
    return response


def transaction_teardown_request(error=None):
    """Rollback transaction on uncaught error. This code should never be
    reached in debug mode, since uncaught errors are raised for use in the
    Werkzeug debugger.
    """
    if view_has_annotation(NO_AUTO_TRANSACTION_ATTR):
        return
    if error is not None and current_atomic:
        current_atomic.__exit__(error.__class__, error, None)


handlers = {
    'before_request': transaction_before_request,
    'after_request': transaction_after_request,
    'teardown_request': transaction_teardown_request,
}
