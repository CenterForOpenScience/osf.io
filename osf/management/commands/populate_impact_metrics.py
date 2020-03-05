import datetime as dt
from random import random
from django.core.management.base import BaseCommand

from osf.metrics import (
    InstitutionProjectCounts,
    PreprintView,
    PreprintDownload,
    UserInstitutionProjectCounts,
)

from osf.models import Institution, OSFUser, Preprint

USERS = None
PREPRINTS = None

# Uncomment and Edit the following guids based off your local environment
USERS = [OSFUser.load('bd53u'), OSFUser.load('hy84n'), OSFUser.load('7zyg2')]
PREPRINTS = [Preprint.load('far32'), Preprint.load('67bzg')]
INSTITUTION = Institution.load('cos')

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


def populate_institution_metrics(dates):
    institution_public_project_count = 25 + (int(25 * random()))
    institution_private_project_count = 25 + (int(25 * random()))
    for date in dates:
        institution_public_project_count = institution_public_project_count - int(5 * random())
        institution_private_project_count = institution_private_project_count - int(5 * random())

        InstitutionProjectCounts.record_institution_project_counts(
            institution=INSTITUTION,
            public_project_count=institution_public_project_count,
            private_project_count=institution_private_project_count,
            timestamp=date
        )

        for user in USERS:
            user_public_project_count = (int(10 * random()))
            user_private_project_count = (int(10 * random()))

            UserInstitutionProjectCounts.record_user_institution_project_counts(
                institution=INSTITUTION,
                user=user,
                public_project_count=user_public_project_count,
                private_project_count=user_private_project_count,
                timestamp=date
            )


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--institutions',
            action='store_true',
            help='Only populate institutions related date'
        )
        parser.add_argument(
            '--preprints',
            action='store_true',
            help='Only populate preprints related date'
        )

    def handle(self, *args, **options):
        today = dt.datetime.today()
        last_seven_days = [(today - dt.timedelta(days=num_days)) for num_days in range(0, 7)]

        if not USERS and not PREPRINTS:
            raise Exception('The USERS or PREPRINTS global variables need to be uncommented and edited for your local environment.')

        if not options['preprints']:
            populate_institution_metrics(last_seven_days)
        if not options['institutions']:
            populate_preprint_metrics(last_seven_days)
