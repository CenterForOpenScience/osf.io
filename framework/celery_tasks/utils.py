from __future__ import unicode_literals

import logging
import inspect
from functools import wraps

from raven import Client

from website import settings

logger = logging.getLogger(__name__)
sentry = Client(dsn=settings.SENTRY_DSN, release=settings.VERSION, tags={'App': 'celery'})

# statuses
FAILED = 'failed'
CREATED = 'created'
STARTED = 'started'
COMPLETED = 'completed'


def log_to_sentry(message, **kwargs):
    if not settings.SENTRY_DSN:
        return logger.warn('send_to_raven called with no SENTRY_DSN')
    return sentry.captureMessage(message, extra=kwargs)

# Use _index here as to not clutter the namespace for kwargs
def dispatch(_event, status, _index=None, **kwargs):
    if _index:
        _event = '{}.{}'.format(_event, _index)

    logger.debug('[{}][{}]{!r}'.format(_event, status, kwargs))


def logged(event, index=None):
    def _logged(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            context = extract_context(func, *args, **kwargs)
            dispatch(event, STARTED, _index=index, **context)
            try:
                res = func(*args, **kwargs)
            except Exception as e:
                if settings.SENTRY_DSN:
                    sentry.captureException()
                dispatch(event, FAILED, _index=index, exception=e, **context)
                raise
            else:
                dispatch(event, COMPLETED, _index=index, **context)
            return res
        return wrapped
    return _logged


def extract_context(func, *args, **kwargs):
    arginfo = inspect.getargspec(func)
    arg_names = arginfo.args
    defaults = {
        arg_names.pop(-1): kwarg
        for kwarg in (arginfo.defaults or [])
    }

    computed_args = zip(arg_names, args)
    if arginfo.varargs:
        computed_args.append(('args', list(args[len(arg_names):])))

    if kwargs:
        defaults['kwargs'] = kwargs

    return dict(computed_args, **defaults)
