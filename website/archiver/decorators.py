import functools

from framework.exceptions import HTTPError

from website.archiver import ARCHIVER_UNCAUGHT_ERROR
from website.archiver.utils import handle_archive_fail

def fail_archive_on_error(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            registration = kwargs['node']
            handle_archive_fail(
                ARCHIVER_UNCAUGHT_ERROR,
                registration.registered_from,
                registration,
                registration.owner,
                str(e)
            )
    return wrapped
