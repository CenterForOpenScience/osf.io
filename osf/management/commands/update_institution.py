from django.core.management.base import BaseCommand
from osf.models import Institution
from scripts.populate_institutions import INSTITUTIONS


def update_institution_rors(env):
    for institution in INSTITUTIONS[env]:
        ror = institution.get('ror')
        if ror:
            institution_obj = Institution.objects.get(_id=institution['_id'])
            institution_obj.ror = ror
            institution_obj.save()


class Command(BaseCommand):
    """
    Add RORs to institution data
    """
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--env',
            dest='env',
            type=str,
            required=True,
            help='The environment, prod, stage, test, whatever.',
        )

    def handle(self, *args, **options):
        env = options.get('env', False)
        update_institution_rors(env)
