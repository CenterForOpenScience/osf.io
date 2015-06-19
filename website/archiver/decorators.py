import functools

from framework.exceptions import HTTPError

from website.project.decorators import _inject_nodes
from website.archiver import ARCHIVER_NETWORK_ERROR
from website.archiver import signals

def fail_archive_on_error(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            _inject_nodes(kwargs)
            registration = kwargs['node']
            registration.archive_status = ARCHIVER_NETWORK_ERROR
            registration.save()
            signals.archive_fail.send(
                registration,
                errors=[e.message]
            )
    return wrapped
