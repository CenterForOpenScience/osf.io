# -*- coding: utf-8 -*-
import hmac
import hashlib

from rest_framework import permissions
from rest_framework.exceptions import ParseError

from framework import sentry
from website import settings


class RequestComesFromMailgun(permissions.BasePermission):
    """Verify that request comes from Mailgun.
    Adapted here from conferences/message.py
    Signature comparisons as recomended from mailgun docs:
    https://documentation.mailgun.com/en/latest/user_manual.html#webhooks
    """
    def has_permission(self, request, view):
        data = request.data
        signature = hmac.new(
            key=settings.MAILGUN_API_KEY,
            msg='{}{}'.format(
                data['timestamp'],
                data['token'],
            ),
            digestmod=hashlib.sha256,
        ).hexdigest()
        if 'signature' not in data:
            exc = 'Signature required in request body'
            sentry.log_exception(exc)
            raise ParseError(exc)
        if not hmac.compare_digest(unicode(signature), unicode(data['signature'])):
            raise ParseError('Invalid signature')
        return True
