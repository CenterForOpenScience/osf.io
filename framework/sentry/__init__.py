#!/usr/bin/env python3
# encoding: utf-8

import logging

from raven.contrib.flask import Sentry

from framework.sessions import get_session

from website import settings

logger = logging.getLogger(__name__)

sentry = Sentry(dsn=settings.SENTRY_DSN)

# Nothing in this module should send to Sentry if debug mode is on
#   or if Sentry isn't configured.
enabled = (not settings.DEBUG_MODE) and settings.SENTRY_DSN


def get_session_data():
    try:
        return get_session().load()
    except (RuntimeError, AttributeError):
        return {}


def log_exception(skip_session=False):
    if not enabled:
        logger.warning('Sentry called to log exception, but is not active')
        return None
    extra = {
        'session': {} if skip_session else get_session_data(),
    }
    return sentry.captureException(extra=extra)


def log_message(message, skip_session=False, extra_data=None, level=logging.ERROR):
    if not enabled:
        logger.warning(
            'Sentry called to log message, but is not active: %s' % message
        )
        return None
    extra = {
        'session': {} if skip_session else get_session_data(),
    }
    if extra_data is None:
        extra_data = {}
    extra.update(extra_data)
    return sentry.captureMessage(message, extra=extra, level=level)
