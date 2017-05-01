"""
Force-archive "stuck" registrations (i.e. failed to completely archive).

Usage:

    # Check if Registration abc12 and qwe34 are stuck
    python -m scripts.force_archive --check abc12 qwe34

    # Dry-run a force-archive of abc12 and qwe34. Verifies that the force-archive can occur.
    python -m scripts.force_archive --dry abc12 qwe34

    # Force-archive abc12 and qwe34
    python -m scripts.force_archive abc12 qwe34
"""
import argparse
import logging
from website.app import setup_django
setup_django()
from django.db import transaction
from django.utils import timezone

from framework.auth import Auth
from website.archiver.tasks import archive
from website.archiver import ARCHIVER_INITIATED
from website.settings import ARCHIVE_TIMEOUT_TIMEDELTA
from osf.models import Registration, NodeLog

from scripts import utils as script_utils

logger = logging.getLogger(__name__)

LOG_WHITELIST = {
    NodeLog.EMBARGO_APPROVED,
    NodeLog.EMBARGO_INITIATED,
    NodeLog.REGISTRATION_APPROVAL_INITIATED,
    NodeLog.REGISTRATION_APPROVAL_APPROVED,
    NodeLog.PROJECT_REGISTERED,
    NodeLog.MADE_PUBLIC,
    NodeLog.EDITED_DESCRIPTION,
}

def force_archive(reg):
    with transaction.atomic():
        for each in reg.node_and_primary_descendants():
            archive_job = each.archive_job
            archive_job.sent = True
            archive_job.save()
            task = archive(archive_job._id)
            task.apply()


class VerificationError(Exception):
    pass


def verify(reg):
    node_logs_after_date = list(
        reg.registered_from.get_aggregate_logs_queryset(Auth(reg.registered_from.creator))
        .filter(date__gt=reg.registered_date)
        .exclude(action__in=LOG_WHITELIST)
        .values_list('action', flat=True)
    )
    if node_logs_after_date:
        raise VerificationError(
            'Original node {} has unexpected logs: {}'.format(reg.registered_from._id,
                                                              node_logs_after_date)
        )
    addons = reg.registered_from.get_addon_names()
    if set(addons) - {'osfstorage', 'wiki'} != set():
        raise VerificationError('Original node has addons: {}'.format(addons))
    return True


def check_registration(reg):
    expired_if_before = timezone.now() - ARCHIVE_TIMEOUT_TIMEDELTA
    archive_job = reg.archive_job
    root_job = reg.root.archive_job
    archive_tree_finished = archive_job.archive_tree_finished()

    if type(archive_tree_finished) is int:
        still_archiving = archive_tree_finished != len(archive_job.children)
    else:
        still_archiving = not archive_tree_finished
    if still_archiving and root_job.datetime_initiated < expired_if_before:
        logger.warn('Registration {} is stuck in archiving'.format(reg._id))
        return False
    else:
        logger.info('Registration {} is not stuck in archiving'.format(reg._id))
        return True


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--dry',
        action='store_true',
        dest='dry_run',
        help='Dry run',
    )
    parser.add_argument(
        '--check',
        action='store_true',
        dest='check',
        help='Check if registrations are stuck',
    )
    parser.add_argument('registration_ids', type=str, nargs='+', help='GUIDs of registrations to archive')
    return parser.parse_args()


def main():
    args = parse_args()
    dry = args.dry_run
    if not dry:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)
    else:
        logger.info('Running in dry mode...')

    checked_ok, checked_stuck = [], []
    verified, skipped = [], []
    for reg_id in args.registration_ids:
        reg = Registration.load(reg_id)
        if args.check:
            not_stuck = check_registration(reg)
            if not_stuck:
                checked_ok.append(reg)
            else:
                checked_stuck.append(reg)
        else:
            try:
                logger.info('Verifying {}'.format(reg._id))
                verify(reg)
            except VerificationError as err:
                logger.error('Skipping {} due to error...'.format(reg._id))
                logger.error(err.args[0])
                skipped.append(reg)
            else:
                verified.append(reg)
                if not dry:
                    logger.info('Force-archiving {}'.format(reg_id))
                    force_archive(reg)
    if checked_ok:
        logger.info('{} registrations not stuck: {}'.format(len(checked_ok), [e._id for e in checked_ok]))
    if checked_stuck:
        logger.warn('{} registrations stuck: {}'.format(len(checked_stuck), [e._id for e in checked_stuck]))

    if verified:
        logger.info('{} registrations {}: {}'.format(
            len(verified),
            'archived' if not dry else 'verified',
            [e._id for e in verified],
        ))
    if skipped:
        logger.error('{} registrations skipped: {}'.format(len(skipped), [e._id for e in skipped]))
    print('Done.')


if __name__ == '__main__':
    main()
