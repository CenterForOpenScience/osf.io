from framework.celery_tasks import app as celery_app
from scripts.analytics.user_summary import UserSummary
from scripts.analytics.node_summary import NodeSummary
from scripts.analytics.institution_summary import InstitutionSummary
from scripts.analytics.base import DateAnalyticsHarness


class SummaryHarness(DateAnalyticsHarness):

    @property
    def analytics_classes(self):
        return [NodeSummary, UserSummary, InstitutionSummary]


@celery_app.task(name='scripts.analytics.run_keen_summaries')
def run_main(date=None, yesterday=False):
    SummaryHarness().main(date, yesterday, False)


if __name__ == '__main__':
    SummaryHarness().main()
