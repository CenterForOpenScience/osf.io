#!/usr/bin/env python
# encoding: utf-8

import sys
import logging
import datetime

from modularodm import Q
from dateutil.relativedelta import relativedelta
from box.client import BoxAuthenticationException

from scripts import utils as scripts_utils
from website.app import init_app
from website.addons.box import model

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_targets(delta):
    return model.BoxOAuthSettings.find(
        Q('expires_at', 'lt', datetime.datetime.utcnow() - delta)
    )


def main(delta, dry_run):
    for record in get_targets(delta):
        logger.info(
            'Refreshing tokens on record {0}; expires at {1}'.format(
                record.user_id,
                record.expires_at.strftime('%c')
            )
        )
        if not dry_run:
            try:
                record.refresh_access_token(force=True)
            except BoxAuthenticationException as ex:
                logger.error(ex.message)


if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    dry_run = 'dry' in sys.argv
    try:
        days = int(sys.argv[2])
    except (IndexError, ValueError, TypeError):
        days = 60 - 7  # refresh tokens are good for 60 days
    delta = relativedelta(days=days)
    # Log to file
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(delta, dry_run=dry_run)
