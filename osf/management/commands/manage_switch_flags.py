import logging
import yaml

from django.core.management.base import BaseCommand
from django.db import transaction
from website import settings

logger = logging.getLogger(__name__)


def manage_waffle(delete_waffle=False, preserve_everyone=True):
    # Inline importation of models is done to so for use in post migrate signal.
    from django.apps import apps
    Flag = apps.get_model('waffle.Flag')
    Switch = apps.get_model('waffle.Switch')

    with transaction.atomic():
        if delete_waffle:
            results = Switch.objects.all().delete()
            logger.info(f'Deleting switches: {results}')
            results = Flag.objects.all().delete()
            logger.info(f'Deleting flags: {results}')

        with open(settings.WAFFLE_VALUES_YAML) as stream:
            features = yaml.safe_load(stream)
        for flag in features['flags']:
            flag.pop('flag_name')

            flag_obj, created = Flag.objects.get_or_create(name=flag['name'], defaults=flag)

            if not created:
                if preserve_everyone:
                    flag.pop('everyone', None)
                for field, value in flag.items():
                    setattr(flag_obj, field, value)
                flag_obj.save()

        for switch in features['switches']:
            switch.pop('flag_name')
            Switch.objects.update_or_create(name=switch['name'], defaults=switch)


class Command(BaseCommand):
    """Ensure all features and switches are updated with the switch and flag files
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '-delete',
            action='store_true',
            help='Use this flag to remove flags; otherwise, the script will just add flags'
        )

        parser.add_argument(
            '--preserve-everyone',
            action='store_true',
            help="Preserve the existing 'everyone' value for flags",
        )

    def handle(self, *args, **options):
        delete_waffle = options.get('delete', False)
        preserve_everyone = options.get('preserve_everyone', True)
        manage_waffle(delete_waffle, preserve_everyone)
