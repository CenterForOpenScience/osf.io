# -*- coding: utf-8 -*-
import logging

from django.core.management.base import BaseCommand

from osf.features import switches, flags
from waffle.models import Flag, Switch

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Ensure all features and switches are updated with the switch and flag files
    """

    def handle(self, *args, **options):
        file_switches = [getattr(switches, switch) for switch in dir(switches) if '__' not in switch]
        current_switches = [switch.name for switch in Switch.objects.all()]

        add_switches = set(file_switches) - set(current_switches)
        for switch in add_switches:
                Switch.objects.get_or_create(name=switch, defaults={'active': False})
                logger.info('Adding switch: {}'.format(switch))

        delete_switches = set(current_switches) - set(file_switches)
        Switch.objects.filter(name__in=delete_switches).delete()
        logger.info('Deleting switches: {}'.format(delete_switches))

        file_flags = [getattr(flags, flag) for flag in dir(flags) if '__' not in flag]
        current_flags = [flag.name for flag in Flag.objects.all()]

        add_flags = set(file_flags) - set(current_flags)
        for flag_name in add_flags:
                Flag.objects.get_or_create(name=flag_name, defaults={'everyone': False})
                logger.info('Adding flag: {}'.format(flag_name))

        delete_flags = set(current_flags) - set(file_flags)
        Flag.objects.filter(name__in=delete_flags).delete()
        logger.info('Deleting flags: {}'.format(delete_flags))
