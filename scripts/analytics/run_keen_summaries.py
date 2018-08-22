import logging
import django
django.setup()

from framework.celery_tasks import app as celery_app
from scripts.analytics.user_summary import UserSummary
from scripts.analytics.node_summary import NodeSummary
from scripts.analytics.file_summary import FileSummary
from scripts.analytics.preprint_summary import PreprintSummary
from scripts.analytics.institution_summary import InstitutionSummary
from scripts.analytics.base import DateAnalyticsHarness
from scripts.utils import add_file_logger

logger = logging.getLogger('scripts.analytics')


class SummaryHarness(DateAnalyticsHarness):

    @property
    def analytics_classes(self):
        return [NodeSummary, FileSummary, UserSummary, InstitutionSummary, PreprintSummary]


@celery_app.task(name='scripts.analytics.run_keen_summaries')
def run_main(date=None, yesterday=False):
    add_file_logger(logger, __file__)
    SummaryHarness().main(date, yesterday, False)


if __name__ == '__main__':
    run_main(yesterday=True)
