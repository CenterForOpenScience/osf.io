"""
This script runs nightly and emails users who want to delete there account with info on how to do so. Users who don't
have any content can be automatically deleted.
"""
import sys
import logging

from website import mails
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from website.app import setup_django
setup_django()
from osf.models import OSFUser
from website.settings import OSF_SUPPORT_EMAIL, OSF_CONTACT_EMAIL

from scripts.utils import add_file_logger

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def deactivate_requested_accounts(dry_run=True):
    users = OSFUser.objects.filter(requested_deactivation=True, contacted_deactivation=False, date_disabled__isnull=True)

    for user in users:
        if user.has_resources:
            mails.send_mail(
                to_addr=OSF_SUPPORT_EMAIL,
                mail=mails.REQUEST_DEACTIVATION,
                user=user,
                can_change_preferences=False,
            )
        else:
            user.disable_account()
            mails.send_mail(
                to_addr=user.username,
                mail=mails.REQUEST_DEACTIVATION_COMPLETE,
                user=user,
                contact_email=OSF_CONTACT_EMAIL,
                can_change_preferences=False,
            )

        user.contacted_deactivation = True
        user.email_last_sent = timezone.now()
        user.save()


@celery_app.task(name='scripts.periodic.deactivate_requested_accounts')
def run_main(dry_run=True):
    if not dry_run:
        add_file_logger(logger, __file__)
    deactivate_requested_accounts(dry_run=dry_run)


if __name__ == '__main__':
    run_main(dry_run='--dry' in sys.argv)
