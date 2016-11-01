# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging
import datetime

from dateutil import relativedelta
from django.utils import timezone

from website.models import Session

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN)


def clear_sessions(max_date, dry_run=False):
    """Remove all sessions last modified before `max_date`.
    """
    session_collection = Session._storage[0].store
    query = {'date_modified': {'$lt': max_date}}
    if dry_run:
        logger.warn('Dry run mode')
    logger.warn(
        'Removing {0} stale sessions'.format(
            session_collection.find(query).count()
        )
    )
    if not dry_run:
        session_collection.remove(query)


def clear_sessions_relative(months=1, dry_run=False):
    """Remove all sessions last modified over `months` months ago.
    """
    logger.warn('Clearing sessions older than {0} months'.format(months))
    now = timezone.now()
    delta = relativedelta.relativedelta(months=months)
    clear_sessions(now - delta, dry_run=dry_run)
