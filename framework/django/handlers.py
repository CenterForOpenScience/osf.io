import logging

from django.db import close_old_connections, reset_queries

logger = logging.getLogger(__name__)


def before_request(*args, **kwargs):
    close_old_connections()
    reset_queries()

def close_connections(*args, **kwargs):
    close_old_connections()

handlers = {
    'before_request': before_request,
    'after_request': close_connections,
    'teardown_request': close_connections,
}
