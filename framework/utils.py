from datetime import datetime
from re import search
from time import time

from django.utils import timezone
from pytz import utc
from werkzeug.utils import secure_filename as werkzeug_secure_filename


def iso8601format(dt):
    """Given a datetime object, return an associated ISO-8601 string"""
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ') if dt else ''


def secure_filename(filename):
    """Return a secure version of a filename.

    Uses ``werkzeug.utils.secure_filename``, but explicitly allows for leading
    underscores.

    :param filename str: A filename to sanitize

    :return: Secure version of filename
    """
    secure = werkzeug_secure_filename(filename)

    # Check for leading underscores, and add them back in
    try:
        secure = search('^_+', filename).group() + secure
    except AttributeError:
        pass

    return secure


def get_timestamp():
    return int(time())


def throttle_period_expired(timestamp, throttle):
    if not timestamp:
        return True
    elif isinstance(timestamp, datetime):
        if timestamp.tzinfo:
            return (timezone.now() - timestamp).total_seconds() > throttle
        else:
            return (timezone.now() - timestamp.replace(tzinfo=utc)).total_seconds() > throttle
    else:
        return (get_timestamp() - timestamp) > throttle
