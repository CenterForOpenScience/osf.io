import logging
import django
django.setup()

from framework.celery_tasks import app as celery_app
from scripts.analytics.base import DateAnalyticsHarness
from scripts.analytics.node_log_events import NodeLogEvents
from scripts.analytics.user_domain_events import UserDomainEvents
from scripts.utils import add_file_logger

logger = logging.getLogger('scripts.analytics')


class EventAnalyticsHarness(DateAnalyticsHarness):

    @property
    def analytics_classes(self):
        return [NodeLogEvents, UserDomainEvents]


@celery_app.task(name='scripts.analytics.run_keen_events')
def run_main(date=None, yesterday=False):
    add_file_logger(logger, __file__)
    EventAnalyticsHarness().main(date, yesterday, False)


if __name__ == '__main__':
    run_main(yesterday=True)
