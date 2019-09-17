# -*- coding: utf-8 -*-
"""Custom exceptions for the framework."""
import copy
from rest_framework import status as http_status
from flask import request
from website import language


class FrameworkError(Exception):
    """Base class from which framework-related errors inherit."""
    pass

class HTTPError(FrameworkError):

    error_msgs = {
        http_status.HTTP_400_BAD_REQUEST: {
            'message_short': 'Bad request',
            'message_long': ('If this should not have occurred and the issue persists, '
                             + language.SUPPORT_LINK),
        },
        http_status.HTTP_403_FORBIDDEN: {
            'message_short': 'Forbidden',
            'message_long': ('You do not have permission to perform this action. '
                             'If this should not have occurred and the issue persists, '
                             + language.SUPPORT_LINK),
        },
        http_status.HTTP_404_NOT_FOUND: {
            'message_short': 'Page not found',
            'message_long': ('The requested resource could not be found. If this '
                             'should not have occurred and the issue persists, '
                             + language.SUPPORT_LINK),
        },
        http_status.HTTP_410_GONE: {
            'message_short': 'Resource deleted',
            'message_long': ('User has deleted this content. If this should '
                             'not have occurred and the issue persists, '
                             + language.SUPPORT_LINK),
        },
        http_status.HTTP_503_SERVICE_UNAVAILABLE: {
            'message_short': 'Service is currently unavailable',
            'message_long': ('The requested service is unavailable. If this '
                             'should not have occurred and the issue persists, '
                             + language.SUPPORT_LINK),
        },
        451: {
            'message_short': 'Content removed',
            'message_long': ('This content has been removed'),
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

    def __repr__(self):
        class_name = self.__class__.__name__
        return '{ClassName}(code={code}, data={data})'.format(
            ClassName=class_name,
            code=self.code,
            data=self.to_data(),
        )

    def __str__(self):
        return repr(self)

    def to_data(self):

        data = copy.deepcopy(self.data)
        if self.code in self.error_msgs:
            data = {
                'message_short': self.error_msgs[self.code]['message_short'],
                'message_long': self.error_msgs[self.code]['message_long']
            }
        elif self.code == http_status.HTTP_401_UNAUTHORIZED:
            data = {
                'message_short': 'Unauthorized',
                'message_long': 'You must <a href="/login/?next={}">log in</a> to access this resource.'.format(request.url),
            }
        else:
            data['message_short'] = 'Unable to resolve'
            data['message_long'] = (
                'OSF was unable to resolve your request. If this issue persists, please report it to '
                + language.SUPPORT_LINK
            )
        data.update(self.data)
        data['code'] = self.code
        data['referrer'] = self.referrer

        return data


class PermissionsError(FrameworkError):
    """Raised if an action cannot be performed due to insufficient permissions
    """
    pass


class TemplateHTTPError(HTTPError):
    """Use in order to pass a specific error template to WebRenderer
    """

    def __init__(self, code, message=None, redirect_url=None, data=None, template=None):
        self.template = template
        super(TemplateHTTPError, self).__init__(code, message, redirect_url, data)
