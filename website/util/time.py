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
