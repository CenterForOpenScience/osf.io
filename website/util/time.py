# -*- coding: utf-8 -*-
from __future__ import absolute_import
import time
from datetime import datetime, timedelta


def get_timestamp():
    return int(time.time())


def throttle_period_expired(timestamp, throttle):
    if not timestamp:
        return True
    elif isinstance(timestamp, datetime):
        return (datetime.utcnow() - timestamp).total_seconds() > throttle
    else:
        return (get_timestamp() - timestamp) > throttle


def generate_expiration_time(duration, base=datetime.utcnow(), utc=False):
    """
    Generate an expiration timestamp
    :param duration: duration in seconds
    :param base: optional base timestamp
    :param utc: optional boolean flag which determines return type
    :return: a timestamp object (default) or a utc string (if utc is set to True)
    """
    if not base:
        base = datetime.utcnow()
    elif not isinstance(base, datetime):
        base = datetime.utcnow()
    expires = base + timedelta(seconds=duration)
    if utc:
        expires = expires.strftime("%a %b %d %H:%M:%S UTC %Y")
    return expires
