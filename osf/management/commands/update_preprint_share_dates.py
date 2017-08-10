from __future__ import unicode_literals
import logging

from django.core.management.base import BaseCommand

from scripts import utils as script_utils
from osf.models import PreprintService
from website.preprints.tasks import on_preprint_updated

logger = logging.getLogger(__name__)

def update_share_preprint_modified_dates(dry_run=False):
    dates_updated = 0
    for preprint in PreprintService.objects.filter():
        if preprint.node.date_modified > preprint.date_modified:
            if not dry_run:
                on_preprint_updated(preprint._id)
            dates_updated += 1
    return dates_updated

class Command(BaseCommand):
    """
    Send more accurate preprint modified dates to Share (max of node.date_modified and preprint.date_modified)
    """
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Say how many preprint updates would be sent to share',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        if not dry_run:
            script_utils.add_file_logger(logger, __file__)
            dates_updated = update_share_preprint_modified_dates()
            logger.info('Sent %d new preprint modified dates to Share' % dates_updated)

        else:
            dates_updated = update_share_preprint_modified_dates(dry_run=True)
            logger.info('Would have sent %d new preprint modified dates to Share' % dates_updated)
