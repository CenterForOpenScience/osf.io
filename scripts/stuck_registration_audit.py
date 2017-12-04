# -*- coding: utf-8 -*-
import io
import os
import csv
import logging
from datetime import datetime

from website.app import setup_django
setup_django()

from django.utils import timezone

from website import mails
from website import settings

from framework.auth import Auth
from framework.celery_tasks import app as celery_app
from osf.management.commands import force_archive as fa
from osf.models import ArchiveJob, Registration
from website.archiver import ARCHIVER_INITIATED
from website.settings import ARCHIVE_TIMEOUT_TIMEDELTA, ADDONS_REQUESTED

from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))

def find_failed_registrations():
    expired_if_before = datetime.utcnow() - ARCHIVE_TIMEOUT_TIMEDELTA
    jobs = ArchiveJob.objects.filter(sent=False, datetime_initiated__lt=expired_if_before, status=ARCHIVER_INITIATED).prefetch_related('dst_node')
    return sorted({
        node.root for node in [job.dst_node for job in jobs]
        if node and node.root
        and not node.root.is_deleted
    }, key=lambda n: n.registered_date)

def analyze_failed_registration_nodes():
    """ If we can just retry the archive, but we can only do that if the
    ORIGINAL node hasn't changed.
    """
    # Get the registrations that are messed up
    failed_registration_nodes = find_failed_registrations()

    # Build up a list of dictionaries with info about these failed nodes
    failed_registration_info = []
    for broken_registration in failed_registration_nodes:
        unacceptable_node_logs_after_date = list(
            broken_registration.registered_from.get_aggregate_logs_queryset(Auth(broken_registration.registered_from.creator))
            .filter(date__gt=broken_registration.registered_date)
            .exclude(action__in=fa.LOG_WHITELIST)
            .exclude(action__in=fa.LOG_GREYLIST)
            .values_list('action', flat=True)
        )

        # Does it have any addons?
        addon_list = [
            addon for addon in ADDONS_REQUESTED
            if broken_registration.registered_from.has_addon(addon)
            and addon not in {'osfstorage', 'wiki'}
        ]
        has_addons = bool(addon_list)

        # Any registrations succeeded after the stuck one?
        # Not sure why broken_registration.registered_from.registrations was always 0 locally...
        succeeded_registrations_after_failed = []
        for other_reg in Registration.objects.filter(
            registered_from=broken_registration.registered_from,
            registered_date__gt=broken_registration.registered_date
        ):
            if other_reg.sanction:
                if other_reg.sanction.is_approved:
                    succeeded_registrations_after_failed.append(other_reg._id)
            else:
                succeeded_registrations_after_failed.append(other_reg._id)

        can_be_reset = fa.verify(broken_registration)
        logger.info('Found broken registration {}'.format(broken_registration._id))
        failed_registration_info.append(
            {
                'registration': broken_registration._id,
                'registered_date': broken_registration.registered_date,
                'original_node': broken_registration.registered_from._id,
                'logs_on_original_after_registration_date': unacceptable_node_logs_after_date,
                'has_addons': has_addons,
                'addon_list': addon_list,
                'succeeded_registrations_after_failed': succeeded_registrations_after_failed,
                'can_be_reset': can_be_reset,
                'registered_from_public': broken_registration.registered_from.is_public,
            }
        )

    return failed_registration_info


def main():
    broken_registrations = analyze_failed_registration_nodes()
    if broken_registrations:
        fieldnames = ['registration', 'registered_date', 'original_node',
                    'logs_on_original_after_registration_date',
                    'has_addons', 'addon_list', 'succeeded_registrations_after_failed', 'can_be_reset',
                    'registered_from_public']
        filename = 'stuck_registrations_{}.csv'.format(timezone.now().isoformat())

        output = io.BytesIO()
        dict_writer = csv.DictWriter(output, fieldnames)
        dict_writer.writeheader()
        dict_writer.writerows(broken_registrations)

        mails.send_mail(
            mail=mails.ARCHIVE_REGISTRATION_STUCK_DESK,
            to_addr=settings.SUPPORT_EMAIL,
            broken_registrations=broken_registrations,
            attachment_name=filename,
            attachment_content=output.getvalue(),
        )

    logger.info('{n} broken registrations found'.format(n=len(broken_registrations)))
    logger.info('Finished.')


@celery_app.task(name='scripts.stuck_registration_audit')
def run_main():
    scripts_utils.add_file_logger(logger, __file__)
    main()

if __name__ == '__main__':
    main()
