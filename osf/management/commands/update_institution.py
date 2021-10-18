import datetime as dt

from django.core.management.base import BaseCommand
from osf.models import Institution
from scripts.populate_institutions import INSTITUTIONS


def update_institution_rors(env):
    for institution in INSTITUTIONS[env]:
        Institution.objects.filter(
            _id=institution['_id']
        ).update(
            ror=institution.get('ror')
        )


class Command(BaseCommand):
    """
    Add RORs to institution data
    """
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--env',
            dest="env",
            type=str,
            required=True,
            help='The enviriorment, prod, stage, test, whatever.',
        )

    def handle(self, *args, **options):
        env = options.get('env', False)
        update_institution_rors(env)
