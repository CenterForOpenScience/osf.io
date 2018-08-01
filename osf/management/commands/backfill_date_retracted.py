# -*- coding: utf-8 -*-
# This is a management command, rather than a migration script, for two primary reasons:
#   1. It makes no changes to database structure (e.g. AlterField), only database content.
#   2. It may need to be ran more than once, as it skips failed registrations.


from datetime import timedelta
import logging

import django
django.setup()

from django.core.management.base import BaseCommand
from django.db import transaction

from osf.models import Registration, Retraction, Sanction
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def set_date_retracted(*args):
    registrations = (
        Registration.objects.filter(retraction__state=Sanction.APPROVED, retraction__date_retracted=None)
        .select_related('retraction')
        .include('registered_from__logs')
        .include('registered_from__guids')
    )
    total = registrations.count()
    logger.info('Migrating {} retractions.'.format(total))

    for registration in registrations:
        if not registration.registered_from:
            logger.warn('Skipping failed registration {}'.format(registration._id))
            continue
        retraction_logs = registration.registered_from.logs.filter(action='retraction_approved', params__retraction_id=registration.retraction._id)
        if retraction_logs.count() != 1 and retraction_logs.first().date - retraction_logs.last().date > timedelta(seconds=5):
            msg = (
                'There should be a retraction_approved log for retraction {} on node {}. No retraction_approved log found.'
                if retraction_logs.count() == 0
                else 'There should only be one retraction_approved log for retraction {} on node {}. Multiple logs found.'
            )
            raise Exception(msg.format(registration.retraction._id, registration.registered_from._id))
        date_retracted = retraction_logs[0].date
        logger.info(
            'Setting date_retracted for retraction {} to be {}, from retraction_approved node log {}.'.format(
                registration.retraction._id, date_retracted, retraction_logs[0]._id
            )
        )
        registration.retraction.date_retracted = date_retracted
        registration.retraction.save()

def unset_date_retracted(*args):
    retractions = Retraction.objects.filter(state=Sanction.APPROVED).exclude(date_retracted=None)
    logger.info('Migrating {} retractions.'.format(retractions.count()))

    for retraction in retractions:
        retraction.date_retracted = None
        retraction.save()


class Command(BaseCommand):
    """
    Backfill Retraction.date_retracted with `RETRACTION_APPROVED` log date.
    """
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run migration and roll back changes to db',
        )
        parser.add_argument(
            '--reverse',
            action='store_true',
            dest='reverse',
            help='Unsets date_retraction'
        )

    def handle(self, *args, **options):
        reverse = options.get('reverse', False)
        dry_run = options.get('dry_run', False)
        if not dry_run:
            script_utils.add_file_logger(logger, __file__)
        with transaction.atomic():
            if reverse:
                unset_date_retracted()
            else:
                set_date_retracted()
            if dry_run:
                raise RuntimeError('Dry run, transaction rolled back.')
