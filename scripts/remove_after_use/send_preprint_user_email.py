# -*- coding: utf-8 -*-
import sys
import logging

import progressbar
from django.core.paginator import Paginator

from website.app import setup_django
setup_django()

from website import mails
from osf.models import PreprintService
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

PAGE_SIZE = 100


def main(dry=True):
    qs = PreprintService.objects.filter(
        is_published=True,
        node__is_deleted=False
    ).select_related('node').prefetch_related('node___contributors').order_by('pk')
    count = qs.count()
    pbar = progressbar.ProgressBar(maxval=count).start()
    contributors_emailed = set()
    logger.info('Sending emails to users for {} published preprints...'.format(count))
    paginator = Paginator(qs, PAGE_SIZE)
    n_processed = 0
    for page_num in paginator.page_range:
        page = paginator.page(page_num)
        for preprint in page.object_list:
            users = preprint.node.contributors.filter(is_active=True)
            for user in users:
                if user._id not in contributors_emailed:
                    if not dry:
                        mails.send_mail(
                            mail=mails.PREPRINT_DOI_CHANGE,
                            to_addr=user.username,
                            can_change_preferences=False,
                            user=user
                        )
                    contributors_emailed.add(user._id)
        n_processed += len(page.object_list)
        pbar.update(n_processed)

    logger.info('Sent email to {} users from {} preprints'.format(len(contributors_emailed), count))


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
