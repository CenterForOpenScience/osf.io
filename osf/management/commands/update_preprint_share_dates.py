from __future__ import unicode_literals
import logging

from django.core.management.base import BaseCommand
from django.db.models import F

from scripts import utils as script_utils
from osf.models import Preprint
from website.preprints.tasks import on_preprint_updated

logger = logging.getLogger(__name__)

def update_share_preprint_modified_dates(dry_run=False):
    for preprint in Preprint.objects.filter(date_modified__lt=F('node__modified')):
        if dry_run:
            logger.info('Would have sent ' + preprint._id + ' data to SHARE')
        else:
            on_preprint_updated(preprint._id)
            logger.info(preprint._id + ' data sent to SHARE')

class Command(BaseCommand):
    """
    Send more accurate preprint modified dates to SHARE (sends updates if preprint.modified < node.modified)
    """
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Say how many preprint updates would be sent to SHARE',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        if not dry_run:
            script_utils.add_file_logger(logger, __file__)
        update_share_preprint_modified_dates(dry_run)
