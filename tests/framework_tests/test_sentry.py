#!/usr/bin/env python
# encoding: utf-8

import mock

from tests.base import OsfTestCase
from tests.factories import UserFactory
from nose.tools import assert_false

import functools

from framework import sentry
from framework.sessions import Session, set_session

from website import settings


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
        session_record = Session()
        set_session(session_record)
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
        session_record = Session()
        session_record.data['auth_user_id'] = user._id
        set_session(session_record)
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
        assert_false(mock_capture.called)
