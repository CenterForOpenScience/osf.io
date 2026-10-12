import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from framework import sentry
from osf.models import Embargo, NodeLog
from osf.models.spam import SpamStatus

logger = logging.getLogger(__name__)


def find_stuck_registrations():
    stuck_embargoes = Embargo.objects.stuck_completed()
    not_spam = []
    spam = []
    for embargo in stuck_embargoes:
        for registration in embargo.registrations.filter(is_deleted=False, is_public=False):
            if registration.spam_status in (SpamStatus.FLAGGED, SpamStatus.SPAM):
                spam.append(registration)
            else:
                not_spam.append(registration)
    return not_spam, spam


def fix_registration(registration):
    with transaction.atomic():
        registration.registered_from.add_log(
            action=NodeLog.EMBARGO_COMPLETED,
            params={
                'project': registration._id,
                'node': registration.registered_from._id,
                'registration': registration._id,
            },
            auth=None,
            save=True,
        )
        for node in registration.node_and_primary_descendants():
            node.set_privacy(node.PUBLIC, auth=None, log=False, save=True)


class Command(BaseCommand):
    help = 'Find (and optionally fix) registrations stuck private by ENG-12078'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Only report counts/guids, do not modify anything',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        not_spam, spam = find_stuck_registrations()

        self.stdout.write(
            f'Found {len(not_spam)} non-spam registration(s) stuck private past their '
            f'embargo end date: {[r._id for r in not_spam]}'
        )
        self.stdout.write(
            f'Found {len(spam)} spam-flagged registration(s) stuck private past their '
            f'embargo end date (left untouched): {[r._id for r in spam]}'
        )

        if dry_run:
            self.stdout.write('Dry run mode, not making any registrations public.')
            return

        for registration in not_spam:
            try:
                fix_registration(registration)
                self.stdout.write(f'Made registration {registration._id} public.')
            except Exception as err:
                logger.exception(err)
                sentry.log_exception(err)
                self.stderr.write(f'Failed to fix registration {registration._id}: {err}')
