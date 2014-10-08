from __future__ import absolute_import
from calendar import timegm
import re

from werkzeug.utils import secure_filename as werkzeug_secure_filename

from email.utils import formatdate


def rfcformat(dt, localtime=False):
    '''Return the RFC822-formatted represenation of a datetime object.

    :param bool localtime: If ``True``, return the date relative to the local
        timezone instead of UTC, properly taking daylight savings time into account.
    '''
    return formatdate(timegm(dt.utctimetuple()), localtime=localtime)


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
