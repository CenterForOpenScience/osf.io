from django.core.management.base import BaseCommand
from django.db.models.expressions import RawSQL
from osf.models import OSFUser


def remove_orcid_from_user_social():
    OSFUser.objects.filter(social__has_key='orcid').update(social=RawSQL("""social #- '{orcid}'""", []))


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        remove_orcid_from_user_social()
