# -*- coding: utf-8 -*-
import logging
import yaml

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


def manage_waffle(delete_waffle=False):
    from django.apps import apps

    Flag = apps.get_model('waffle.Flag')
    Switch = apps.get_model('waffle.Switch')

    with open('osf/features.yaml', 'r') as stream:
        features = yaml.safe_load(stream)
    for flag in features['flags']:
        flag.pop('flag_name')
        Flag.objects.get_or_create(name=flag['name'], defaults=flag)
    for switch in features['switches']:
        switch.pop('flag_name')
        Switch.objects.get_or_create(name=switch['name'], defaults=switch)

    if delete_waffle:
        results = Switch.objects.exclude(name__in=[switch['name'] for switch in features['switches']]).delete()
        logger.info(f'Deleting switches: {results}')

        results = Flag.objects.exclude(name__in=[flag['name'] for flag in features['flags']]).delete()
        logger.info(f'Deleting flags: {results}')


class Command(BaseCommand):
    """Ensure all features and switches are updated with the switch and flag files
    """

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '-delete',
            action='store_true',
            help='Use this flag to remove flags, otherwise the script will just add flags'
        )

    def handle(self, *args, **options):
        delete_waffle = options.get('delete', False)
        manage_waffle(delete_waffle)
