import re
from typing import Final
from collections.abc import Iterable

import pytz
import time
from datetime import datetime

from bleach.sanitizer import Cleaner, ALLOWED_TAGS, ALLOWED_PROTOCOLS, ALLOWED_ATTRIBUTES
from bleach.css_sanitizer import CSSSanitizer, ALLOWED_CSS_PROPERTIES
from django.utils import timezone
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
        secure = re.search('^_+', filename).group() + secure
    except AttributeError:
        pass

    return secure


_sentinel: Final = object()


def sanitize_html(
    text: str,
    tags: set[str] = ALLOWED_TAGS,
    attributes: dict[str, Iterable[str]] | Iterable[str] = _sentinel,
    protocols: set[str] = ALLOWED_PROTOCOLS,
    strip: bool = False,
    styles: set[str] | None = ALLOWED_CSS_PROPERTIES,
    strip_comments: bool = True,
    filters: list = None,
) -> str:
    css_sanitizer = None
    if attributes == _sentinel:
        attributes = ALLOWED_ATTRIBUTES
    if styles is not None:
        css_sanitizer = CSSSanitizer(allowed_css_properties=styles)
    cleaner = Cleaner(
        tags=tags,
        attributes=attributes,
        protocols=protocols,
        strip=strip,
        strip_comments=strip_comments,
        css_sanitizer=css_sanitizer,
        filters=filters,
    )
    return cleaner.clean(text)


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
