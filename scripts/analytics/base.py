import time
import logging
import argparse
import importlib
from datetime import datetime, timedelta
from dateutil.parser import parse

from website.app import init_app
from website.settings import KEEN as keen_settings
from keen.client import KeenClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class BaseAnalytics(object):

    @property
    def collection_name(self):
        raise NotImplementedError('Must specify a Keen event collection name')

    @property
    def analytic_type(self):
        raise NotImplementedError('Must specify the analytic type for logging purposes')

    def get_events(self, date):
        raise NotImplementedError('You must define a get_events method to gather analytic events')

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

        logger.info('Gathering {} analytics for the {} collection for {}'.format(
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
        parser.add_argument('-d', '--date', dest='date')
        parser.add_argument('-y', '--yesterday', dest='yesterday', action='store_true')

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


class BaseAnalyticsHarness(object):

    def __init__(self):
        init_app(routes=False)

    @property
    def analytics_classes(self):
        raise NotImplementedError("Please specify a default set of classes to run with this analytics harness")

    def parse_args(self):
        parser = argparse.ArgumentParser(description='Populate keen analytics!')
        parser.add_argument(
            '-as', '--analytics_scripts', nargs='+', dest='analytics_scripts', required=False,
            help='Enter the names of scripts inside scripts/analytics you would like to run separated by spaces (ex: -as user_summary node_summary)'
        )
        return parser.parse_args()

    def try_to_import_from_args(self, entered_scripts):
        imported_script_classes = []
        for script in entered_scripts:
            try:
                script_events = importlib.import_module('scripts.analytics.{}'.format(script))
                imported_script_classes.append(script_events.get_class())
            except (ImportError, NameError) as e:
                logger.error(e)
                logger.error(
                    'Error importing script - make sure the script specified is inside of scripts/analytics. '
                    'Also make sure the main analytics class name is the same as the script name but in camel case. '
                    'For example, the script named  scripts/analytics/addon_snapshot.py has class AddonSnapshot'
                )

            return imported_script_classes

    def main(self, command_line=True):
        analytics_classes = self.analytics_classes
        if command_line:
            args = self.parse_args()
            if args.analytics_scripts:
                analytics_classes = self.try_to_import_from_args(args.analytics_scripts)

        for analytics_class in analytics_classes:
            class_instance = analytics_class()
            events = class_instance.get_events()
            class_instance.send_events(events)


class DateAnalyticsHarness(BaseAnalyticsHarness):

    def parse_args(self):
        parser = argparse.ArgumentParser(description='Populate keen analytics!')
        parser.add_argument(
            '-as', '--analytics_scripts', nargs='+', dest='analytics_scripts', required=False,
            help='Enter the names of scripts inside scripts/analytics you would like to run separated by spaces (ex: -as user_summary node_summary)'
        )
        parser.add_argument('-d', '--date', dest='date', required=False)
        parser.add_argument('-y', '--yesterday', dest='yesterday', action='store_true')
        return parser.parse_args()

    def main(self, date=None, yesterday=False, command_line=True):
        analytics_classes = self.analytics_classes
        if yesterday:
            date = (datetime.today() - timedelta(1)).date()

        if command_line:
            args = self.parse_args()
            if args.yesterday:
                date = (datetime.today() - timedelta(1)).date()
            if not date:
                try:
                    date = parse(args.date).date()
                except AttributeError:
                    raise AttributeError('You must either specify a date or use the yesterday argument to gather analytics for yesterday.')
            if args.analytics_scripts:
                analytics_classes = self.try_to_import_from_args(args.analytics_scripts)

        for analytics_class in analytics_classes:
            class_instance = analytics_class()
            events = class_instance.get_events(date)
            class_instance.send_events(events)
