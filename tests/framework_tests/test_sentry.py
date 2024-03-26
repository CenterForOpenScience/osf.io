#!/usr/bin/env python3

from unittest import mock
from django.conf import settings as django_conf_settings
from importlib import import_module

from tests.base import OsfTestCase
from osf_tests.factories import UserFactory

import functools

from framework import sentry

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore


def set_sentry(status):
    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            enabled, sentry.enabled = sentry.enabled, status
            func(*args, **kwargs)
            sentry.enabled = enabled
        return wrapped
    return wrapper


with_sentry = set_sentry(True)
without_sentry = set_sentry(False)

@with_sentry
@mock.patch('framework.sentry.sentry.captureException')
def test_log_no_request_context(mock_capture):
    sentry.log_exception()
    mock_capture.assert_called_with(extra={'session': {}})


class TestSentry(OsfTestCase):

    @with_sentry
    @mock.patch('framework.sentry.sentry.captureException')
    def test_log_not_logged_in(self, mock_capture):
        sentry.log_exception()
        mock_capture.assert_called_with(
            extra={
                'session': {},
            },
        )

    @with_sentry
    @mock.patch('framework.sentry.sentry.captureException')
    def test_log_logged_in(self, mock_capture):
        user = UserFactory()
        s = SessionStore()
        s['auth_user_id'] = user._id
        s.create()
        self.context.g.current_session = s
        sentry.log_exception()
        mock_capture.assert_called_with(
            extra={
                'session': {
                    'auth_user_id': user._id,
                },
            },
        )

    @without_sentry
    @mock.patch('framework.sentry.sentry.captureException')
    def test_log_not_enabled(self, mock_capture):
        sentry.log_exception()
        assert not mock_capture.called
