import logging
import inspect
from functools import wraps

from sentry_sdk import init, configure_scope, capture_message, set_context, capture_exception
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.flask import FlaskIntegration

from website import settings

logger = logging.getLogger(__name__)

init(
    dsn=settings.SENTRY_DSN,
    integrations=[CeleryIntegration(), DjangoIntegration(), FlaskIntegration()],
    release=settings.VERSION,
)
with configure_scope() as scope:
    scope.set_tag('App', 'celery')

# statuses
FAILED = 'failed'
CREATED = 'created'
STARTED = 'started'
COMPLETED = 'completed'


def log_to_sentry(message, **kwargs):
    if not settings.SENTRY_DSN:
        return logger.warning('log_to_sentry called with no SENTRY_DSN')
    if kwargs:
        set_context('extra', kwargs)
    return capture_message(message)


# Use _index here as to not clutter the namespace for kwargs
def dispatch(_event, status, _index=None, **kwargs):
    if _index:
        _event = f'{_event}.{_index}'

    logger.debug(f'[{_event}][{status}]{kwargs!r}')


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
                    capture_exception(e)
                dispatch(event, FAILED, _index=index, exception=e, **context)
                raise
            else:
                dispatch(event, COMPLETED, _index=index, **context)
            return res
        return wrapped
    return _logged


def extract_context(func, *args, **kwargs):
    arginfo = inspect.getfullargspec(func)
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
