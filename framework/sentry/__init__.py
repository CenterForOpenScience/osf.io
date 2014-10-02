import logging

from raven.contrib.flask import Sentry

from framework.sessions import get_session

from website import settings

logger = logging.getLogger(__name__)

sentry = Sentry(dsn=settings.SENTRY_DSN)

# Nothing in this module should send to Sentry if debug mode is on
#   or if Sentry isn't configured.
enabled = (not settings.DEBUG_MODE) and settings.SENTRY_DSN


def log_exception():
    if not enabled:
        logger.warning('Sentry called to log exception, but is not active')
        return None

    return sentry.captureException(extra={
        'session': get_session().data,
    })


def log_message(message):
    if not enabled:
        logger.warning(
            'Sentry called to log message, but is not active: %s' % message
        )
        return None

    return sentry.captureMessage(message, extra={
        'session': get_session().data,
    })
