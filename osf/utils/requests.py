import requests
from django.db import transaction
from flask import Request as FlaskRequest
from flask import request
from rest_framework.permissions import SAFE_METHODS
from api.base.api_globals import api_globals
from api.base import settings
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

class DummyRequest:
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
    # Temporary Notes: not sure why `get_session()` was used directly instead of `session`
    from framework.sessions import get_session

    req = get_current_request()
    user_id = None
    if isinstance(req, FlaskRequest):
        user_session = get_session()
        user_id = user_session.get('auth_user_id', None)
    elif hasattr(req, 'user'):
        # admin module can return a user w/o an id
        user_id = getattr(req.user, '_id', None)
    return req, user_id


def get_headers_from_request(req):
    """ Get and normalize DRF and Flask request headers
    """
    headers = getattr(req, 'META', {})
    if headers:
        headers = {
            '-'.join([part.capitalize() for part in k.split('_')]).replace('Http-', ''): v
            for k, v in headers.items()
        }
        remote_addr = (headers.get('X-Forwarded-For') or headers.get('Remote-Addr'))
        headers['Remote-Addr'] = remote_addr.split(',')[0].strip() if remote_addr else None
    else:
        headers = getattr(req, 'headers', {})
        headers = {
            k: v
            for k, v in headers.items()
        }
        headers['Remote-Addr'] = getattr(req, 'remote_addr', None)
    return headers


def string_type_request_headers(req):
    request_headers = {}
    if not isinstance(req, DummyRequest):
        request_headers = {
            k: v
            for k, v in get_headers_from_request(req).items()
            if isinstance(v, str)
        }
    return request_headers


def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    """
    https://www.peterbe.com/plog/best-practice-with-retries-with-requests
    """
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session
