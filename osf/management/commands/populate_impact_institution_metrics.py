import datetime as dt
from random import random
from django.core.management.base import BaseCommand

from osf.metrics import (
    InstitutionProjectCounts,
    UserInstitutionProjectCounts,
)

from osf.models import Institution, OSFUser


# Edit the following guids based off your local environment
USERS = [OSFUser.load('bd53u'), OSFUser.load('hy84n'), OSFUser.load('7zyg2')]
INSTITUTION = Institution.load('cos')


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

    def handle(self, *args, **options):
        today = dt.datetime.today()
        last_seven_days = [(today - dt.timedelta(days=num_days)) for num_days in range(0, 7)]

        populate_institution_metrics(last_seven_days)
