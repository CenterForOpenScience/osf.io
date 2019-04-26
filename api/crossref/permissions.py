# -*- coding: utf-8 -*-
import hmac
import hashlib

from rest_framework import permissions
from rest_framework import exceptions

from framework import sentry
from website import settings


class RequestComesFromMailgun(permissions.BasePermission):
    """Verify that request comes from Mailgun.
    Adapted here from conferences/message.py
    Signature comparisons as recomended from mailgun docs:
    https://documentation.mailgun.com/en/latest/user_manual.html#webhooks
    """
    def has_permission(self, request, view):
        if request.method != 'POST':
            raise exceptions.MethodNotAllowed(method=request.method)
        data = request.data
        if not data:
            raise exceptions.ParseError('Request body is empty')
        if not settings.MAILGUN_API_KEY:
            return False
        signature = hmac.new(
            key=settings.MAILGUN_API_KEY,
            msg='{}{}'.format(
                data['timestamp'],
                data['token'],
            ),
            digestmod=hashlib.sha256,
        ).hexdigest()
        if 'signature' not in data:
            error_message = 'Signature required in request body'
            sentry.log_message(error_message)
            raise exceptions.ParseError(error_message)
        if not hmac.compare_digest(str(signature), str(data['signature'])):
            raise exceptions.ParseError('Invalid signature')
        return True
