from __future__ import absolute_import

from email.utils import formatdate
from calendar import timegm


def rfcformat(dt, localtime=False):
    '''Return the RFC822-formatted represenation of a datetime object.

    :param bool localtime: If ``True``, return the date relative to the local
        timezone instead of UTC, properly taking daylight savings time into account.
    '''
    return formatdate(timegm(dt.utctimetuple()), localtime=localtime)
