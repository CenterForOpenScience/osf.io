import functools

from framework.exceptions import HTTPError

from website.project.decorators import _inject_nodes
from website.archiver import ARCHIVER_UNCAUGHT_ERROR
from website.archiver import utils

def fail_archive_on_error(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            _inject_nodes(kwargs)
            registration = kwargs['node']
            utils.handle_archive_fail(
                ARCHIVER_UNCAUGHT_ERROR,
                registration.registered_from,
                registration,
                registration.registered_user,
                str(e)
            )
    return wrapped
