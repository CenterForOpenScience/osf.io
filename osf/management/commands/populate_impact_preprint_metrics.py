import datetime as dt
from random import random
from django.core.management.base import BaseCommand

from osf.metrics import (
    PreprintView,
    PreprintDownload,
)

from osf.models import Preprint


"""
This management command can be run to populate impact with fake
preprints metrics data.

All flags are optional with the script defaulting to 3 preprints from
your local database with metrics for the past 7 days and an average
count of 25 for preprint views/downloads per day.

--preprints: Specify preprint guids
--num_preprints: Specify the number of preprint to use from the database (if
preprint guids aren't specified)
--days: Specify the number of days to write metrics data for
--group_counts: Indicates that metric counts should be grouped
in a single record per preprint per day
--avg_counts: The average number of view/download counts to write
for each preprint per day

Example: docker-compose run --rm web python3 manage.py populate_impact_preprint_metrics --num_preprints 1 --days 5 --group_counts --avg_counts 50
"""


def populate_preprint_metrics(preprints, dates, avg_counts, group_counts=False):
    for date in dates:
        for preprint in preprints:
            preprint_view_count = int((avg_counts * 2) * random())
            preprint_download_count = int((avg_counts * 2) * random())

            if group_counts:
                PreprintView.record_for_preprint(
                    preprint=preprint,
                    path=preprint.primary_file.path,
                    timestamp=date,
                    count=preprint_view_count
                )

                PreprintDownload.record_for_preprint(
                    preprint=preprint,
                    path=preprint.primary_file.path,
                    timestamp=date,
                    count=preprint_download_count
                )
            else:
                for count in range(preprint_view_count):
                    PreprintView.record_for_preprint(
                        preprint=preprint,
                        path=preprint.primary_file.path,
                        timestamp=date
                    )

                for count in range(preprint_download_count):
                    PreprintDownload.record_for_preprint(
                        preprint=preprint,
                        path=preprint.primary_file.path,
                        timestamp=date
                    )


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--preprints',
            nargs='*',
            help='Specify preprints guids'
        )
        parser.add_argument(
            '--num_preprints',
            type=int,
            default=3,
            help='Specify number of preprints to use if not specifying preprints'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Specify number of past days to write metrics data for'
        )
        parser.add_argument(
            '--group_counts',
            action='store_true',
            help='Group counts in metric records for fewer ES requests'
        )
        parser.add_argument(
            '--avg_counts',
            type=int,
            default=25,
            help='Average number of counts to write per day per preprint'
        )

    def handle(self, *args, **options):
        days = options.get('days')
        num_preprints = options.get('num_preprints')
        group_counts = options.get('group_counts')
        avg_counts = options.get('avg_counts')

        if options.get('preprints'):
            preprints = Preprint.objects.filter(guids___id__in=options.get('preprints'))
        else:
            preprints = Preprint.objects.all()[:num_preprints]

        today = dt.datetime.today()
        last_x_days = [(today - dt.timedelta(days=num_days)) for num_days in range(0, days)]

        populate_preprint_metrics(preprints, last_x_days, avg_counts, group_counts)
