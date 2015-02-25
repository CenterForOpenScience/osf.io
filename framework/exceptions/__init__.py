# -*- coding: utf-8 -*-
'''Custom exceptions for the framework.'''
import copy
import httplib as http
from flask import request

class FrameworkError(Exception):
    """Base class from which framework-related errors inherit."""
    pass

class HTTPError(FrameworkError):

    error_msgs = {
        http.BAD_REQUEST: {
            'message_short': 'Bad request',
            'message_long': ('If this should not have occurred and the issue persists, '
            'please report it to <a href="mailto:support@osf.io">support@osf.io</a>.'),
        },
        http.UNAUTHORIZED: {
            'message_short': 'Unauthorized',
            'message_long': 'You must <a href="/login/">log in</a> to access this resource.',
        },
        http.FORBIDDEN: {
            'message_short': 'Forbidden',
            'message_long': ('You do not have permission to perform this action. '
                'If this should not have occurred and the issue persists, '
                'please report it to <a href="mailto:support@osf.io">support@osf.io</a>.'),
        },
        http.NOT_FOUND: {
            'message_short': 'Page not found',
            'message_long': ('The requested resource could not be found. If this '
                'should not have occurred and the issue persists, please report it '
                'to <a href="mailto:support@osf.io">support@osf.io</a>.'),
        },
        http.GONE: {
            'message_short': 'Resource deleted',
            'message_long': ('The requested resource has been deleted. If this should '
                'not have occurred and the issue persists, please report it to '
                '<a href="mailto:support@osf.io">support@osf.io</a>.'),
        },
        http.SERVICE_UNAVAILABLE: {
            'message_short': 'Service is currently unavailable',
            'message_long': ('The requested service is unavailable. If this should '
                'not have occurred and the issue persists, please report it to '
                '<a href="mailto:support@osf.io">support@osf.io</a>.'),
        },
    }

    def __init__(self, code, message=None, redirect_url=None, data=None):

        super(HTTPError, self).__init__(message)

        self.code = code
        self.redirect_url = redirect_url
        self.data = data or {}

        try:
            self.referrer = request.referrer
        except RuntimeError:
            self.referrer = None

    def to_data(self):

        data = copy.deepcopy(self.data)
        if self.code in self.error_msgs:
            data = {
                'message_short': self.error_msgs[self.code]['message_short'],
                'message_long': self.error_msgs[self.code]['message_long']
            }
        else:
            data['message_short'] = 'Unable to resolve'
            data['message_long'] = ('OSF was unable to resolve your request. If this '
                'issue persists, please report it to '
                '<a href="mailto:support@osf.io">support@osf.io</a>.')
        data.update(self.data)
        data['code'] = self.code
        data['referrer'] = self.referrer

        return data


class PermissionsError(FrameworkError):
    """Raised if an action cannot be performed due to insufficient permissions
    """
    pass
