# -*- coding: utf-8 -*-
"""HMAC signature utilities.
"""
# TODO: move this module to utils directory once rubeus.py's circular import issue is resolved
from itsdangerous import URLSafeSerializer

from website import settings

# Use the website's secret key
serializer = URLSafeSerializer(settings.SECRET_KEY)


def sign(payload):
    """Sign a payload."""
    return serializer.dumps(payload)


def load(data):
    """Unsign a payload."""
    return serializer.loads(data)
