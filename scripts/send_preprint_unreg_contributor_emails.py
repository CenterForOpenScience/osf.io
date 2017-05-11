# -*- coding: utf-8 -*-
"""Sends an unregistered user claim email for preprints created after 2017-03-14. A hotfix was made on that
date which caused unregistered user claim emails to not be sent. The regression was fixed on 2017-05-05. This
sends the emails that should have been sent during that time period.

NOTE: This script should only be run ONCE.
"""
import sys
import logging
import datetime as dt
import pytz
from framework.auth import Auth

from website.app import init_app
init_app(routes=False)

from website.project import signals as project_signals
from scripts import utils as script_utils
from website.project.views import contributor  # flake8: noqa (set up listeners)

from osf.models import PreprintService

logger = logging.getLogger(__name__)
logging.getLogger('website.mails.mails').setLevel(logging.CRITICAL)

# datetime at which https://github.com/CenterForOpenScience/osf.io/commit/568413a77cc51511a0f7afe081a218676a36ebb6 was committed
START_DATETIME = dt.datetime(2017, 3, 14, 19, 10, tzinfo=pytz.utc)
# datetime at which https://github.com/CenterForOpenScience/osf.io/commit/38513916bb9584eb723c46e35553dc6d2c267e1a was deployed
END_DATETIME = dt.datetime(2017, 5, 5, 5, 48, tzinfo=pytz.utc)

def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)
    count = 0
    preprints = PreprintService.objects.filter(
        is_published=True,
        date_published__gte=START_DATETIME,
        date_published__lte=END_DATETIME
    ).order_by('date_published').distinct().select_related('node', 'node__creator')
    for preprint in preprints:
        auth = Auth(preprint.node.creator)
        for author in preprint.node.contributors.filter(is_active=False):
            assert not author.is_registered
            logger.info('Sending email to unregistered User {} on PreprintService {}'.format(author._id, preprint._id))
            if not dry_run:
                project_signals.contributor_added.send(
                    preprint.node,
                    contributor=author,
                    auth=auth,
                    email_template='preprint'
                )
            count += 1
    logger.info('Sent an email to {} unregistered users'.format(count))

if __name__ == '__main__':
    main()
