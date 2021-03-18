"""Resend all resources (nodes, registrations, preprints) for given providers to SHARE."""
import logging

from django.core.management.base import BaseCommand
from osf.models import AbstractProvider, AbstractNode, Preprint
from api.share.utils import update_share

logger = logging.getLogger(__name__)


def reindex_provider(provider):
    preprints = Preprint.objects.filter(provider=provider)
    if preprints:
        logger.info('Sending {} preprints to SHARE...'.format(provider.preprints.count()))
        for preprint in preprints:
            update_share(preprint)

    nodes = AbstractNode.objects.filter(provider=provider)
    if nodes:
        logger.info('Sending {} AbstractNodes to SHARE...'.format(AbstractNode.objects.filter(provider=provider).count()))
        for abstract_node in nodes:
            update_share(abstract_node)


class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--providers', type=str, nargs='+', help='Provider _ids')
        parser.add_argument('--type', type=str, help='what type of provider to reindex', default=None)

    def handle(self, *args, **options):
        provider_ids = options.get('providers', [])
        type = options.get('type', None)

        if type:
            providers = AbstractProvider.objects.filter(type__contains=type, _id__in=provider_ids)
        else:
            providers = AbstractProvider.objects.filter(_id__in=provider_ids)

        for provider in providers:
            logger.info('Reindexing {}...'.format(provider._id))
            reindex_provider(provider)
