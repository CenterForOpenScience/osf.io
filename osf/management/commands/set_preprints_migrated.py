import logging

from django.core.management.base import BaseCommand

from osf.models import PreprintProvider

logger = logging.getLogger(__name__)


def set_preprints_migrated(provider_id, is_migrated=True):
    """Set `is_migrated` on every preprint of the provider, all versions included."""
    provider = PreprintProvider.load(provider_id)
    if not provider:
        raise RuntimeError(f'Could not find preprint provider {provider_id}')

    updated = provider.preprints.update(is_migrated=is_migrated)
    logger.info(f'Set is_migrated={is_migrated} on {updated} preprints of provider {provider_id}')


class Command(BaseCommand):
    help = 'Mark all preprints of a provider as migrated off OSF, or unmark them with --unset.'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--provider-id',
            dest='provider_id',
            required=True,
            help='ID of the preprint provider, e.g. psyarxiv',
        )
        parser.add_argument(
            '--unset',
            action='store_true',
            help='Set is_migrated back to false',
        )

    def handle(self, *args, **options):
        set_preprints_migrated(options['provider_id'], is_migrated=not options['unset'])
