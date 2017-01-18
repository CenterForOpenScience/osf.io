import logging

from django.db import close_old_connections, reset_queries

logger = logging.getLogger(__name__)


def before_request(*args, **kwargs):
    reset_queries()
    close_old_connections()

def teardown_request(*args, **kwargs):
    close_old_connections()

handlers = {
    'before_request': before_request,
    'teardown_request': teardown_request,
}
