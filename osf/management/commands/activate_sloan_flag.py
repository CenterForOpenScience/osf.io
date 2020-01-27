# -*- coding: utf-8 -*-
import logging

from django.core.management.base import BaseCommand
from waffle.models import Flag

logger = logging.getLogger(__name__)

from osf.features import (
    SLOAN_DATA,
    SLOAN_PREREG,
    SLOAN_COI
)

SLOAN_FLAGS = [
    SLOAN_DATA,
    SLOAN_PREREG,
    SLOAN_COI
]


def activate_single_flag(flag_name, value):
    # Only on flag at a time.
    Flag.objects.filter(name__in=SLOAN_FLAGS).update(everyone=False)

    flag = Flag.objects.get(name=flag_name)
    flag.everyone = value
    flag.save()


class Command(BaseCommand):
    """Flips sloan flags on and off, ensures only one flag is active at any given time.
    """

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--flag_name',
            '-f',
            type=str,
            dest='flag_name',
            help='The name of the flag you want to activate',
            required=True
        )
        parser.add_argument(
            '--turn_on',
            action='store_true',
            help='The value of the \'everyone\' attribute for the flag,'
                 ' not including this will turn all sloan flags off.',
        )

    def handle(self, *args, **options):
        flag_name = options['flag_name']
        value = options['flag_value']
        activate_single_flag(flag_name, value)
