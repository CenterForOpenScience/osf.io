import datetime

from website.app import init_app

import django
django.setup()

from scripts.analytics.download_count_summary import DownloadCountSummary


def main():
    init_app()

    download_count_summary = DownloadCountSummary()
    date = datetime.date(2018, 1, 1)

    while date < datetime.date.today():
        events = download_count_summary.get_events(date)
        download_count_summary.send_events(events)
        date += datetime.timedelta(days=1)


if __name__ == '__main__':
    main()
