import datetime as dt
from random import random
from django.core.management.base import BaseCommand

from osf.metrics import (
    PreprintView,
    PreprintDownload,
)

from osf.models import OSFUser, Preprint


# Edit the following guids based off your local environment
USERS = [OSFUser.load('bd53u'), OSFUser.load('hy84n'), OSFUser.load('7zyg2')]
PREPRINTS = [Preprint.load('far32'), Preprint.load('67bzg')]

def populate_preprint_metrics(dates):
    for date in dates:
        for user in USERS:
            for preprint in PREPRINTS:
                preprint_view_count = int(10 * random())
                PreprintView.record_for_preprint(
                    preprint=preprint,
                    user=user,
                    path=preprint.primary_file.path,
                    timestamp=date,
                    count=preprint_view_count
                )

                preprint_download_count = int(10 * random())
                PreprintDownload.record_for_preprint(
                    preprint=preprint,
                    user=user,
                    path=preprint.primary_file.path,
                    timestamp=date,
                    count=preprint_download_count
                )


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--institutions',
            help='Only populate institutions related date'
        )

    def handle(self, *args, **options):
        today = dt.datetime.today()
        last_seven_days = [(today - dt.timedelta(days=num_days)) for num_days in range(0, 7)]

        populate_preprint_metrics(last_seven_days)
