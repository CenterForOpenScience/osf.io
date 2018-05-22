# -*- coding: utf-8 -*-
import hmac
import hashlib

from rest_framework import permissions
from django.core.exceptions import PermissionDenied

from website import settings


class RequestComesFromMailgun(permissions.BasePermission):
    """Verify that request comes from Mailgun.
    Adapted here from conferences/message.py"""

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
        if signature != data['signature']:
            raise PermissionDenied('Invalid headers on incoming mail')
        return True
