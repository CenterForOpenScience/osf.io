from raven.contrib.flask import Sentry

from framework.sessions import get_session

from website import settings

sentry = Sentry(dsn=settings.SENTRY_DSN)


def log_exception():
    sentry.captureException(extra={
        'session': get_session().data
    })

