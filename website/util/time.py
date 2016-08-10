# -*- coding: utf-8 -*-
from __future__ import absolute_import
import time
from datetime import datetime
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
            return (datetime.utcnow() - timestamp).total_seconds() > throttle
    else:
        return (get_timestamp() - timestamp) > throttle
