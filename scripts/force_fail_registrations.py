"""
Forcefully marks a registration as failed. Use to
remove "stuck" registrations. USE WITH CARE.

Usage:

    # Check if Registration abc12 and qwe34 are stuck
    python -m scripts.force_fail_registrations --check abc12 qwe34

    # Force-fail abc12 and qwe34
    python -m scripts.force_fail_registrations abc12 qwe34
"""
import argparse
import logging

from django.db import transaction

from website.app import setup_django
setup_django()
from osf.models import Registration
from website.archiver import ARCHIVER_FORCED_FAILURE
from website.archiver.listeners import archive_fail
from scripts import utils as script_utils
from scripts.force_archive import check_registration

logger = logging.getLogger(__name__)

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
    force_failed = []
    for reg_id in args.registration_ids:
        logger.info('Processing registration {}'.format(reg_id))
        reg = Registration.load(reg_id)
        is_stuck = not check_registration(reg)
        if args.check:
            if is_stuck:
                checked_stuck.append(reg)
            else:
                checked_ok.append(reg)
        else:
            if not is_stuck:
                logger.info('Registration {} is not stuck, skipping...'.format(reg))
                continue

            logger.warn('Failing registration {}'.format(reg_id))
            if not dry:
                with transaction.atomic():
                    archive_job = reg.archive_job
                    archive_job.sent = False
                    archive_job.save()
                    reg.archive_status = ARCHIVER_FORCED_FAILURE
                    archive_fail(reg, errors=reg.archive_job.target_info())
                    force_failed.append(reg)
    if checked_ok:
        logger.info('{} registrations not stuck: {}'.format(len(checked_ok), [e._id for e in checked_ok]))
    if checked_stuck:
        logger.warn('{} registrations stuck: {}'.format(len(checked_stuck), [e._id for e in checked_stuck]))

    if force_failed:
        logger.info('Force-failed {} registrations: {}'.format(len(force_failed), [e._id for e in force_failed]))
    print('Done.')


if __name__ == '__main__':
    main()
