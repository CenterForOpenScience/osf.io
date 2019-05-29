import logging
import django
django.setup()

from framework.celery_tasks import app as celery_app
from scripts.analytics.base import BaseAnalyticsHarness
from scripts.analytics.addon_snapshot import AddonSnapshot
from scripts.utils import add_file_logger

logger = logging.getLogger('scripts.analytics')

class SnapshotHarness(BaseAnalyticsHarness):

    @property
    def analytics_classes(self):
        return [AddonSnapshot]


@celery_app.task(name='scripts.analytics.run_keen_snapshots')
def run_main():
    add_file_logger(logger, __file__)
    SnapshotHarness().main(command_line=False)

if __name__ == '__main__':
    run_main()
