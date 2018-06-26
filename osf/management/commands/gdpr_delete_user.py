"""Delete a user to GDPR specifications


    python manage.py gdpr_delete_user guid1

Erroring deletions will be logged and skipped.
"""
import logging

logger = logging.getLogger(__name__)

from django.core.management.base import BaseCommand
from osf.models import OSFUser

class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('guids', type=str, nargs='+', help='user guid to be deleted')

    def handle(self, *args, **options):
        guids = options.get('guids', None)

        for guid in guids:
            try:
                user = OSFUser.load(guid)
                user.gdpr_delete()
                user.save()
            except Exception as exc:
                logger.info(exc)
