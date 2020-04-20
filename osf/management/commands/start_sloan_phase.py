"""
Switches Sloan user tags, Switches and Flags into a state where the Sloan study can begin.
"""
import logging
from osf.models import (
    Tag,
)

from waffle.models import (
    Flag,
    Switch
)
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)

WAFFLE = 'waffle:sloan|{}'
NO_WAFFLE = 'no_waffle:sloan|{}'
FLAG_NAME = 'sloan_{}_display'
SWITCH_NAME = 'sloan_{}_input'
AVAILABLE_FLAGS = ['coi', 'data', 'prereg']


def flip(flag):
    try:
        waffle_tag = Tag.all_tags.get(system=True, name=WAFFLE.format(flag))
        waffle_tag.osfuser_set.clear()
        logger.info(f'Tag {WAFFLE.format(flag)} cleared')
    except Tag.DoesNotExist:
        logger.info(f'Tag {WAFFLE.format(flag)} not found')
        pass
    try:
        no_waffle_tag = Tag.all_tags.get(system=True, name=NO_WAFFLE.format(flag))
        no_waffle_tag.osfuser_set.clear()
        logger.info(f'Tag {NO_WAFFLE.format(flag)} cleared')
    except Tag.DoesNotExist:
        logger.info(f'Tag {NO_WAFFLE.format(flag)} not found')
        pass
    waffle_flag, created = Flag.objects.get_or_create(name=FLAG_NAME.format(flag))
    waffle_flag.percent = 50
    waffle_flag.everyone = None
    waffle_flag.save()

    waffle_switch, created = Switch.objects.get_or_create(name=SWITCH_NAME.format(flag))
    waffle_switch.active = True
    waffle_switch.save()

    logger.info(f'Enabled {waffle_flag} at {timezone.now()}')


class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--flag',
            type=str,
            help='Flags to be updated',
            required=True
        )
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run migration and roll back changes to db',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', True)
        flag = options.get('flag', None)
        assert flag in AVAILABLE_FLAGS, f'the given flag : \'{flag}\' was invalid'
        with transaction.atomic():
            flip(flag)
            if dry_run:
                raise Exception('[Dry Run] Transactions rolledback.')
