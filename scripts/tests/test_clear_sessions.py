from django.utils import timezone
from nose.tools import *  # noqa
from tests.base import OsfTestCase

class TestClearSessions(OsfTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestClearSessions, cls).setUpClass()
        cls.session_collection = Session._storage[0].store

    def setUp(self):
        super(TestClearSessions, self).setUp()
        now = timezone.now()
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

