#!/usr/bin/env python
# encoding: utf-8

import sys
import logging
import datetime

from modularodm import Q
from dateutil.relativedelta import relativedelta

from scripts import utils as scripts_utils
from website.app import init_app
from website.oauth.models import ExternalAccount
from website.addons.base.exceptions import AddonError
from website.addons.box.model import Box

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_targets(delta):
    # NOTE: expires_at is the  access_token's expiration date,
    # NOT the refresh token's
    return ExternalAccount.find(
        Q('expires_at', 'lt', datetime.datetime.utcnow() - delta) &
        Q('provider', 'eq', 'box')
    )


def main(delta, dry_run):
    for record in get_targets(delta):
        logger.info(
            'Refreshing tokens on record {0}; expires at {1}'.format(
                record._id,
                record.expires_at.strftime('%c')
            )
        )
        if not dry_run:
            try:
                Box(record).refresh_oauth_key(force=True)
            except AddonError as ex:
                logger.error(ex.message)


if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    dry_run = 'dry' in sys.argv
    try:
        days = int(sys.argv[2])
    except (IndexError, ValueError, TypeError):
        days = 60 - 7  # refresh tokens that expire this week
    delta = relativedelta(days=days)
    # Log to file
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(delta, dry_run=dry_run)
