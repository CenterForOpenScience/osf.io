import django
django.setup()

import datetime

from admin.metrics.views import FileDownloadCounts
from framework.celery_tasks import app as celery_app
from website import settings
from website.app import init_app

from keen import KeenClient


@celery_app.task(name='scripts.analytics.keen_download_number')
def main():

    client = KeenClient(
        project_id=settings.KEEN['private']['project_id'],
        read_key=settings.KEEN['private']['read_key'],
    )

    number_downloads_total = client.count(
        eventCollection='file_stats',
        timeframe='previous_1_days',
        filters=[
            {
                'property_name': 'action.type',
                'operator': 'eq',
                'property_value': 'download_file',
                'timezone': "UTC"
            }
        ]
    )
    number_downloads_unique = client.count_unique(
        eventCollection='file_stats',
        timeframe='previous_1_days',
        filters=[
            {
                'property_name': 'action.type',
                'operator': 'eq',
                'property_value': 'download_file',
                'timezone': "UTC"
            }
        ]
    )

    FileDownloadCounts.update(
        number_downloads_total=number_downloads_total,
        number_downloads_unique=number_downloads_unique,
        update_date=datetime.datetime.now()
    )

if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    main()