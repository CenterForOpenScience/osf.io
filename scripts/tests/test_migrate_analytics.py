import pytz
from dateutil.parser import parse
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from scripts.analytics.migrate_analytics import generate_events_between_events, fill_in_event_gaps


class TestMigrateAnalytics(OsfTestCase):
    def setUp(self):
        super(TestMigrateAnalytics, self).setUp()

        self.day_one = parse('2016-03-12').replace(tzinfo=pytz.UTC)
        self.day_two = parse('2016-03-16').replace(tzinfo=pytz.UTC)
        self.day_three = parse('2016-03-19').replace(tzinfo=pytz.UTC)

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
                "total": 5,
                "connected": 4,
                "disconnected": 1
            }
        }

        self.keen_event_3 = {
            "keen": {
                "timestamp": self.day_three.isoformat(),
                "created_at": self.day_three.isoformat(),
                "id": 2
            },
            "nodes": {
                "deleted": 0,
                "total": 8,
                "connected": 6,
                "disconnected": 2
            }
        }

    def test_generate_events_between_events(self):
        generated_events = generate_events_between_events([self.day_one, self.day_two], self.keen_event)

        # Only for the first gap, so 3/13, 3/14, 3/15
        assert_equal(len(generated_events), 3)
        returned_dates = [event['keen']['timestamp'] for event in generated_events]
        expected_dates = ['2016-03-{}T00:00:00+00:00'.format(i) for i in range(13, 16)]
        assert_items_equal(returned_dates, expected_dates)

        # check the totals are the same as the first event
        returned_totals = [event['nodes']['total'] for event in generated_events]
        expected_totals = [self.keen_event["nodes"]["total"] for i in range(len(generated_events))]
        assert_items_equal(returned_totals, expected_totals)

    def test_fill_in_event_gaps(self):
        filled_in_events = fill_in_event_gaps('test', [self.keen_event, self.keen_event_2, self.keen_event_3])

        # Should generate for 5 days total - 3/13, 3/14, 3/15, 3/17 and  3/18
        assert_equal(len(filled_in_events), 5)

        returned_dates = [event['keen']['timestamp'] for event in filled_in_events]
        expected_dates = ['2016-03-{}T00:00:00+00:00'.format(i) for i in range(13, 16)]
        expected_dates += ['2016-03-{}T00:00:00+00:00'.format(i) for i in range(17, 19)]
        assert_items_equal(returned_dates, expected_dates)
