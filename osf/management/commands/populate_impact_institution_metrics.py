import datetime as dt
from random import random
from django.core.management.base import BaseCommand

from osf.metrics import (
    InstitutionProjectCounts,
    UserInstitutionProjectCounts,
)

from osf.models import Institution, OSFUser


"""
This management command can be run to populate impact with fake
institutional metrics data.

All flags are optional with the script defaulting to 3 users and 1 institution
from your local database with metrics for the past 7 days.

--users: Specify user guids
--num_users: Specify the number of users to use from the database (if
user guids aren't specified)
--institutions: Specify institution guids
--num_institutions: Specify the number of institutions to use from the database
(if institution guids aren't specified)
--days: Specify the number of days to write metrics data for

Example: docker-compose run --rm web python3 manage.py populate_impact_institution_metrics --days 3 --institutions cos --users hy84n bd53u
"""


def populate_institution_metrics(users, institutions, dates):
    institution_public_project_count = 25 + (int(25 * random()))
    institution_private_project_count = 25 + (int(25 * random()))

    for date in dates:

        for institution in institutions:
            institution_public_project_count = institution_public_project_count - int(5 * random())
            institution_private_project_count = institution_private_project_count - int(5 * random())

            InstitutionProjectCounts.record_institution_project_counts(
                institution=institution,
                public_project_count=institution_public_project_count,
                private_project_count=institution_private_project_count,
                timestamp=date
            )

            for user in users:
                user_public_project_count = (int(10 * random()))
                user_private_project_count = (int(10 * random()))

                UserInstitutionProjectCounts.record_user_institution_project_counts(
                    institution=institution,
                    user=user,
                    public_project_count=user_public_project_count,
                    private_project_count=user_private_project_count,
                    timestamp=date
                )


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--users',
            nargs='*',
            help='Specify user guids'
        )
        parser.add_argument(
            '--num_users',
            type=int,
            default=3,
            help='Specify number of users to use if not specifying users'
        )
        parser.add_argument(
            '--institutions',
            nargs='*',
            help='Specify insitutions guids'
        )
        parser.add_argument(
            '--num_institutions',
            type=int,
            default=1,
            help='Specify number of institutions to use if not specifying institutions'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Specify number of past days to write metrics data for'
        )

    def handle(self, *args, **options):
        days = options.get('days')
        num_users = options.get('num_users')
        num_institutions = options.get('num_institutions')

        if options.get('users'):
            users = OSFUser.objects.filter(guids___id__in=options.get('users'))
        else:
            users = OSFUser.objects.all()[:num_users]

        if options.get('institutions'):
            institutions = Institution.objects.filter(_id__in=options.get('institutions'))
        else:
            institutions = Institution.objects.all()[:num_institutions]

        today = dt.datetime.today()
        last_x_days = [(today - dt.timedelta(days=num_days)) for num_days in range(0, days)]

        populate_institution_metrics(users, institutions, last_x_days)
