#!/usr/bin/env python3

import logging
from typing import Literal

from sentry_sdk import init, capture_exception, capture_message, isolation_scope
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.flask import FlaskIntegration

from framework.sessions import get_session
from website import settings

logger = logging.getLogger(__name__)
enabled = (not settings.DEBUG_MODE) and settings.SENTRY_DSN

if enabled:
    sentry = init(
        dsn=settings.SENTRY_DSN,
        integrations=[CeleryIntegration(), DjangoIntegration(), FlaskIntegration()],
    )

LOG_LEVEL_MAP: dict[int, Literal['debug', 'info', 'warning', 'error', 'critical']] = {
    logging.DEBUG: 'debug',
    logging.INFO: 'info',
    logging.WARNING: 'warning',
    logging.ERROR: 'error',
    logging.CRITICAL: 'critical'
}

# Nothing in this module should send to Sentry if debug mode is on
#   or if Sentry isn't configured.


def get_session_data():
    try:
        return get_session().load()
    except (RuntimeError, AttributeError):
        return {}


def log_exception(exception: Exception, skip_session=False):
    if not enabled:
        logger.warning('Sentry called to log exception, but is not active')
        return None
    extra = {
        'session': {} if skip_session else get_session_data(),
    }
    with isolation_scope() as scope:
        for key, value in extra.items():
            scope.set_extra(key, value)
        return capture_exception(exception)


def log_message(message, skip_session=False, extra_data=None, level=logging.ERROR):
    if not enabled:
        logger.warning(
            'Sentry called to log message, but is not active: %s' % message
        )
        return None
    extra = {
        'session': None if skip_session else get_session_data(),
    }
    if extra_data is not None:
        extra.update(extra_data)
    with isolation_scope() as scope:
        for key, value in extra.items():
            scope.set_extra(key, value)
        level_str = LOG_LEVEL_MAP.get(level, 'error')
        return capture_message(message, level=level_str)
