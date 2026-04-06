from django.core.management.base import BaseCommand
from django.db.models.expressions import RawSQL
from osf.models import OSFUser
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def remove_orcid_from_user_social():
    start = datetime.now()
    orcid_records = OSFUser.objects.filter(social__has_key='orcid')
    logger.info(f'extracted orcid records count {orcid_records.count()}')
    deleted_records = orcid_records.update(social=RawSQL("""social #- '{orcid}'""", []))
    logger.info(f'deleted orcid records count {deleted_records} in {datetime.now() - start}')


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        remove_orcid_from_user_social()
