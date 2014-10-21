from __future__ import absolute_import
import re

from werkzeug.utils import secure_filename as werkzeug_secure_filename


def iso8601format(dt):
    """Given a datetime object, return an associated ISO-8601 string"""
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


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
