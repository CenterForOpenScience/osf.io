from framework.celery_tasks import app as celery_app
from scripts.analytics.base import BaseAnalyticsHarness
from scripts.analytics.addon_snapshot import AddonSnapshot


class SnapshotHarness(BaseAnalyticsHarness):

    @property
    def analytics_classes(self):
        return [AddonSnapshot]


@celery_app.task(name='scripts.analytics.run_keen_snapshots')
def run_main():
    SnapshotHarness().main(command_line=False)

if __name__ == '__main__':
    SnapshotHarness().main()
