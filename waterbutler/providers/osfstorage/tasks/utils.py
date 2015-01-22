import os
import glob
import errno
import logging
import functools
import contextlib
import subprocess

from celery.utils.log import get_task_logger

from waterbutler.core import exceptions
from waterbutler.tasks.app import app, client
from waterbutler.providers.osfstorage import settings


logger = get_task_logger(__name__)
logger.setLevel(logging.INFO)


def ensure_path(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def ensure_paths():
    paths = [
        settings.FILE_PATH_PENDING,
        settings.FILE_PATH_COMPLETE,
    ]
    for path in paths:
        ensure_path(path)


def create_parity_files(file_path, redundancy=5):
    """
    :raise: `ParchiveError` if creation of parity files fails
    """
    path, name = os.path.split(file_path)
    with open(os.devnull, 'wb') as DEVNULL:
        ret_code = subprocess.call(
            [
                'par2',
                'c',
                '-r{0}'.format(redundancy),
                os.path.join(path, '{0}.par2'.format(name)),
                file_path,
            ],
            stdout=DEVNULL,
            stderr=DEVNULL,
        )
        if ret_code != 0:
            raise exceptions.ParchiveError()
        return [
            os.path.abspath(fpath)
            for fpath in
            glob.glob(os.path.join(path, '{0}*.par2'.format(name)))
        ]


def sanitize_request(request):
    """Return dictionary of request attributes, excluding args and kwargs. Used
    to ensure that potentially sensitive values aren't logged or sent to Sentry.
    """
    return {
        key: value
        for key, value in vars(request).items()
        if key not in ['args', 'kwargs']
    }


def _log_task(func):
    """Decorator to add standardized logging to Celery tasks. Decorated tasks
    must also be decorated with `bind=True` so that `self` is available.
    """
    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        logger.info(sanitize_request(self.request))
        return func(self, *args, **kwargs)
    return wrapped


def _create_task(*args, **kwargs):
    """Decorator factory combining `_log_task` and `task(bind=True, *args,
    **kwargs)`. Return a decorator that turns the decorated function into a
    Celery task that logs its calls.
    """
    def wrapper(func):
        wrapped = _log_task(func)
        wrapped = app.task(bind=True, *args, **kwargs)(wrapped)
        return wrapped
    return wrapper


def task(*args, **kwargs):
    """Decorator or decorator factory for logged tasks. If passed a function,
    decorate it; if passed anything else, return a decorator.
    """
    if len(args) == 1 and callable(args[0]):
        return _create_task()(args[0])
    return _create_task(*args, **kwargs)


def get_countdown(attempt, init_delay, max_delay, backoff):
    multiplier = backoff ** attempt
    return min(init_delay * multiplier, max_delay)


def capture_retry_message(task):
    if not client:
        return
    client.captureException(extra=sanitize_request(task.request))


@contextlib.contextmanager
def RetryTask(task, attempts, init_delay, max_delay, backoff, warn_idx, error_types):
    try:
        yield
    except error_types as exc_value:
        try_count = task.request.retries
        if warn_idx is not None and try_count >= warn_idx:
            capture_retry_message(task)
        countdown = get_countdown(try_count, init_delay, max_delay, backoff)
        task.max_retries = attempts
        raise task.retry(exc=exc_value, countdown=countdown)


RetryUpload = functools.partial(
    RetryTask,
    attempts=settings.UPLOAD_RETRY_ATTEMPTS,
    init_delay=settings.UPLOAD_RETRY_INIT_DELAY,
    max_delay=settings.UPLOAD_RETRY_MAX_DELAY,
    backoff=settings.UPLOAD_RETRY_BACKOFF,
    warn_idx=settings.UPLOAD_RETRY_WARN_IDX,
    error_types=(Exception,),
)

RetryHook = functools.partial(
    RetryTask,
    attempts=settings.HOOK_RETRY_ATTEMPTS,
    init_delay=settings.HOOK_RETRY_INIT_DELAY,
    max_delay=settings.HOOK_RETRY_MAX_DELAY,
    backoff=settings.HOOK_RETRY_BACKOFF,
    warn_idx=settings.UPLOAD_RETRY_WARN_IDX,
    error_types=(Exception,),
)

RetryParity = functools.partial(
    RetryTask,
    attempts=settings.PARITY_RETRY_ATTEMPTS,
    init_delay=settings.PARITY_RETRY_INIT_DELAY,
    max_delay=settings.PARITY_RETRY_MAX_DELAY,
    backoff=settings.PARITY_RETRY_BACKOFF,
    warn_idx=settings.PARITY_RETRY_WARN_IDX,
    error_types=(Exception,),
)
