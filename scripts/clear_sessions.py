# -*- coding: utf-8 -*-

import logging
import datetime

from dateutil import relativedelta
from modularodm import Q

from website.models import Session

from nose.tools import *
from tests.base import OsfTestCase


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
    now = datetime.datetime.utcnow()
    delta = relativedelta.relativedelta(months=months)
    clear_sessions(now - delta, dry_run=dry_run)


class TestClearSessions(OsfTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestClearSessions, cls).setUpClass()
        cls.session_collection = Session._storage[0].store

    def setUp(self):
        super(TestClearSessions, self).setUp()
        now = datetime.datetime.utcnow()
        self.dates = [
            now,
            now - relativedelta.relativedelta(months=2),
            now - relativedelta.relativedelta(months=4),
        ]
        self.sessions = [Session() for _ in range(len(self.dates))]
        for session in self.sessions:
            session.save()
        # Manually set `date_created` fields in MongoDB.
        for idx, date in enumerate(self.dates):
            self.session_collection.update(
                {'_id': self.sessions[idx]._id},
                {'$set': {'date_modified': date}},
            )
        Session._clear_caches()
        assert_equal(
            Session.find().count(),
            3,
        )

    def tearDown(self):
        super(TestClearSessions, self).tearDown()
        Session.remove()

    def test_clear_sessions(self):
        clear_sessions(self.dates[1])
        assert_equal(
            Session.find().count(),
            2,
        )

    def test_clear_sessions_relative(self):
        clear_sessions_relative(3)
        assert_equal(
            Session.find().count(),
            2,
        )

