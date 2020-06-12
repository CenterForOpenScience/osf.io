# -*- coding: utf-8 -*-
import logging

from django.core.management.base import BaseCommand

from osf.features import switches, flags
from waffle.models import Flag, Switch

logger = logging.getLogger(__name__)

def manage_waffle(delete_waffle=False):
    file_switches = list(switches.values())
    current_switches = Switch.objects.values_list('name', flat=True)

    add_switches = set(file_switches) - set(current_switches)
    for switch in add_switches:
        Switch.objects.get_or_create(name=switch, defaults={'active': False})
        logger.info('Adding switch: {}'.format(switch))

    file_flags = list(flags.values())
    current_flags = Flag.objects.values_list('name', flat=True)

    add_flags = set(file_flags) - set(current_flags)
    for flag_name in add_flags:
        Flag.objects.get_or_create(name=flag_name, defaults={'everyone': False})
        logger.info('Adding flag: {}'.format(flag_name))

    if delete_waffle:
        delete_switches = set(current_switches) - set(file_switches)
        Switch.objects.filter(name__in=delete_switches).delete()
        logger.info('Deleting switches: {}'.format(delete_switches))

        delete_flags = set(current_flags) - set(file_flags)
        Flag.objects.filter(name__in=delete_flags).delete()
        logger.info('Deleting flags: {}'.format(delete_flags))

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
