from __future__ import unicode_literals
import logging

from django.db import close_old_connections, reset_queries

logger = logging.getLogger(__name__)


def reset_django_db_queries_and_close_connections(*args, **kwargs):
    reset_queries()
    close_old_connections()

def close_old_django_db_connections(resp=None):
    close_old_connections()

    return resp

handlers = {
    'before_request': reset_django_db_queries_and_close_connections,
    'after_request': close_old_django_db_connections,
    'teardown_request': close_old_django_db_connections,
}
