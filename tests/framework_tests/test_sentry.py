#!/usr/bin/env python3

from unittest import mock
from unittest.mock import sentinel

from django.conf import settings as django_conf_settings
from importlib import import_module

from tests.base import OsfTestCase
from osf_tests.factories import UserFactory

import functools
from flask import g
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
@mock.patch('framework.sentry.isolation_scope')
@mock.patch('framework.sentry.capture_exception')
def test_log_no_request_context(mock_capture, push_scope_mock):
    sentry.log_exception(sentinel.exception)
    push_scope_mock.return_value.__enter__.return_value.set_extra.assert_called_once_with('session', {})
    mock_capture.assert_called_with(sentinel.exception)


class TestSentry(OsfTestCase):

    @with_sentry
    @mock.patch('framework.sentry.isolation_scope')
    @mock.patch('framework.sentry.capture_exception')
    def test_log_not_logged_in(self, mock_capture, push_scope_mock):
        sentry.log_exception(sentinel.exception)
        push_scope_mock.return_value.__enter__.return_value.set_extra.assert_called_once_with('session', {})
        mock_capture.assert_called_with(sentinel.exception)

    @with_sentry
    @mock.patch('framework.sentry.isolation_scope')
    @mock.patch('framework.sentry.capture_exception')
    def test_log_logged_in(self, mock_capture, push_scope_mock):
        user = UserFactory()
        s = SessionStore()
        s['auth_user_id'] = user._id
        s.create()
        g.current_session = s
        sentry.log_exception(sentinel.exception)
        push_scope_mock.return_value.__enter__.return_value.set_extra.assert_called_once_with(
            'session', {'auth_user_id': user._id,}
        )
        mock_capture.assert_called_once_with(sentinel.exception)

    @without_sentry
    @mock.patch('framework.sentry.isolation_scope')
    @mock.patch('framework.sentry.capture_exception')
    def test_log_not_enabled(self, mock_capture, push_scope_mock):
        sentry.log_exception(sentinel.exception)
        push_scope_mock.assert_not_called()
        mock_capture.assert_not_called()
