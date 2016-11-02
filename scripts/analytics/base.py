import time
import logging
import argparse
from datetime import datetime

from website.app import init_app
from website.settings import KEEN as keen_settings
from keen.client import KeenClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class BaseAnalytics(object):

    def __init__(self):
        init_app()

    @property
    def collection_name(self):
        raise NotImplementedError('Must specify a Keen event collection name')

    @property
    def analytic_type(self):
        raise NotImplementedError('Must specify the analytic type for logging purposes')

    def get_events(self, date):
        pass

    def send_events(self, events):
        keen_project = keen_settings['private']['project_id']
        write_key = keen_settings['private']['write_key']
        if keen_project and write_key:
            client = KeenClient(
                project_id=keen_project,
                write_key=write_key,
            )
            logger.info('Adding {} events to the {} collection'.format(len(events), self.collection_name))
            client.add_events({self.collection_name: events})
        else:
            logger.info('Keen not enabled - would otherwise be adding the following {} events to the {} collection'.format(len(events), self.collection_name))
            print(events)


class SnapshotAnalytics(BaseAnalytics):

    @property
    def analytic_type(self):
        return 'snapshot'

    def get_events(self, date=None):
        if date:
            raise AttributeError('Snapshot analytics may not be called with a date.')

        logger.info('Gathering {} analytics for the {} collection'.format(self.analytic_type, self.collection_name))


class SummaryAnalytics(BaseAnalytics):

    @property
    def analytic_type(self):
        return 'summary'

    def get_events(self, date):
        # Date must be specified, must be a date (not a datetime), and must not be today or in the future
        if not date:
            raise AttributeError('Script must be called with a date to gather analytics.')
        today = datetime.today().date()
        if date >= today:
            raise AttributeError('Script cannot be called for the same day, or for a date in the future.')
        if type(date) != type(today):
            raise AttributeError('Please call the script using a date object, not a datetime object')

        logger.info('Gathering {} analytics for the {} collection up until {}'.format(
            self.analytic_type,
            self.collection_name,
            date.isoformat()
        ))

    def parse_args(self):
        parser = argparse.ArgumentParser(
            description='Enter the date to gather {} analytics for the {} collection'.format(
                self.analytic_type,
                self.collection_name
            )
        )
        parser.add_argument('-d', '--date', dest='date', required=False)

        return parser.parse_args()


class EventAnalytics(SummaryAnalytics):

    @property
    def analytic_type(self):
        return 'event'

    def yield_chunked_events(self, events):
        """ The keen API likes events in chunks no bigger than 5000 -
        Only yield that many at a time.
        """
        for i in range(0, len(events), 5000):
            yield events[i:i + 5000]

    def send_events(self, events):
        keen_project = keen_settings['private']['project_id']
        write_key = keen_settings['private']['write_key']
        if keen_project and write_key:
            client = KeenClient(
                project_id=keen_project,
                write_key=write_key,
            )
            logger.info('Adding {} events to the {} collection'.format(len(events), self.collection_name))

            for chunk in self.yield_chunked_events(events):
                client.add_events({self.collection_name: chunk})
                time.sleep(1)

        else:
            logger.info(
                'Keen not enabled - would otherwise be adding the following {} events to the {} collection'.format(
                    len(events), self.collection_name
                )
            )
            print(events)
