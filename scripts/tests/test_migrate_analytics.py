import datetime
from dateutil.parser import parse
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from scripts.analytics.migrate_analytics import generate_events_between_events


class TestMigrateAnalytics(OsfTestCase):
    def setUp(self):
        super(TestMigrateAnalytics, self).setUp()

        self.day_one = parse('2016-03-12')
        self.day_two = parse('2016-03-16')

        self.keen_event = {
            "keen": {
                "timestamp": self.day_one.isoformat(),
                "created_at": self.day_one.isoformat(),
                "id": 1
            },
            "nodes": {
                "deleted": 0,
                "total": 1,
                "connected": 1,
                "disconnected": 0
            }
        }

        self.keen_event_2 = {
            "keen": {
                "timestamp": self.day_two.isoformat(),
                "created_at": self.day_two.isoformat(),
                "id": 2
            },
            "nodes": {
                "deleted": 0,
                "total": 1,
                "connected": 1,
                "disconnected": 0
            }
        }

    def test_generate_events_between_events(self):
        generated_events = generate_events_between_events([self.day_one, self.day_two], self.keen_event_2)
        assert_equal(len(generated_events), 3)
        returned_dates = [event['keen']['timestamp'] for event in generated_events]
        expected_dates = ['2016-03-{}T00:00:00'.format(i) for i in range(13, 16)]
        assert_items_equal(returned_dates, expected_dates)
