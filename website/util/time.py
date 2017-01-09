# -*- coding: utf-8 -*-
from __future__ import absolute_import
from datetime import datetime
import pytz
import time

from django.utils import timezone


def get_timestamp():
    return int(time.time())


def throttle_period_expired(timestamp, throttle):
    if not timestamp:
        return True
    elif isinstance(timestamp, datetime):
        if timestamp.tzinfo:
            return (timezone.now() - timestamp).total_seconds() > throttle
        else:
            return (timezone.now() - timestamp.replace(tzinfo=pytz.utc)).total_seconds() > throttle
    else:
        return (get_timestamp() - timestamp) > throttle
