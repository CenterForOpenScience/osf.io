# -*- coding: utf-8 -*-
import sys
import logging

from website.app import setup_django
setup_django()
from website import mails
from osf.models import OSFUser
from addons.mendeley.models import UserSettings
import progressbar

from scripts import utils as script_utils

logger = logging.getLogger(__name__)


def main(dry=True):
    qs = UserSettings.objects.filter(owner__is_active=True).select_related('owner').order_by('pk')
    count = qs.count()
    pbar = progressbar.ProgressBar(maxval=count).start()
    logger.info('Sending email to {} users'.format(count))
    for i, each in enumerate(qs):
        user = each.owner
        logger.info('Sending email to OSFUser {}'.format(user._id))
        if not dry:
            mails.send_mail(
                mail=mails.MENDELEY_REAUTH,
                to_addr=user.username,
                can_change_preferences=False,
                user=user
            )
        pbar.update(i + 1)
    logger.info('Sent email to {} users'.format(count))

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
