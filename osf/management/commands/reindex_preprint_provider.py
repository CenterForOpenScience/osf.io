"""Resend all preprints for given providers to SHARE."""
import logging

from django.core.management.base import BaseCommand
from osf.models import PreprintProvider
from website.preprints.tasks import update_preprint_share

logger = logging.getLogger(__name__)

def reindex_provider(provider):
    logger.info('Sending {} preprints to SHARE...'.format(provider.preprints.count()))
    for preprint in provider.preprints.all():
        update_preprint_share(preprint, old_subjects=None, share_type=None)

class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('providers', type=str, nargs='+', help='Provider _ids')

    def handle(self, *args, **options):
        provider_ids = options.get('providers', [])
        for provider in PreprintProvider.objects.filter(_id__in=provider_ids):
            logger.info('Reindexing {}...'.format(provider._id))
            reindex_provider(provider)
