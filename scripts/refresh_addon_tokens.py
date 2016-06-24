#!/usr/bin/env python
# encoding: utf-8

import logging
import datetime
import time

from modularodm import Q
from oauthlib.oauth2 import InvalidGrantError
from dateutil.relativedelta import relativedelta

from framework.celery_tasks import app as celery_app

from scripts import utils as scripts_utils

from website.app import init_app
from website.addons.box.model import Box
from website.addons.googledrive.model import GoogleDriveProvider
from website.addons.mendeley.model import Mendeley
from website.oauth.models import ExternalAccount

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

PROVIDER_CLASSES = (Box, GoogleDriveProvider, Mendeley, )


def look_up_provider(addon_short_name):
    for Provider in PROVIDER_CLASSES:
        if Provider.short_name == addon_short_name:
            return Provider
    return None

def get_targets(delta, addon_short_name):
    # NOTE: expires_at is the  access_token's expiration date,
    # NOT the refresh token's
    return ExternalAccount.find(
        Q('expires_at', 'lt', datetime.datetime.utcnow() - delta) &
        Q('provider', 'eq', addon_short_name)
    )

def main(delta, Provider, rate_limit, dry_run):
    allowance = rate_limit[0]
    last_call = time.time()
    for record in get_targets(delta, Provider.short_name):
        if Provider(record).has_expired_credentials:
            logger.info(
                'Found expired record {}, skipping'.format(record.__repr__())
            )
            continue

        logger.info(
            'Refreshing tokens on record {0}; expires at {1}'.format(
                record.__repr__(),
                record.expires_at.strftime('%c')
            )
        )
        if not dry_run:
            if allowance < 1:
                try: 
                    time.sleep(rate_limit[1] - (time.time() - last_call))
                except ValueError:
                    pass  # ValueError indicates a negative sleep time
                allowance = rate_limit[0]

            allowance -= 1
            last_call = time.time()
            success = False
            try:
                success = Provider(record).refresh_oauth_key(force=True)
            except InvalidGrantError as e:
                logger.error(e)
            else:
                logger.info(
                    'Status of record {}: {}'.format(
                        record.__repr__(),
                        'SUCCESS' if success else 'FAILURE')
                )


@celery_app.task(name='scripts.refresh_addon_tokens')
def run_main(addons=None, rate_limit=(5, 1), dry_run=True):
    """
    :param dict addons: of form {'<addon_short_name>': int(<refresh_token validity duration in days>)}
    :param tuple rate_limit: of form (<requests>, <seconds>). Default is five per second
    """
    init_app(set_backends=True, routes=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    for addon in addons:
        try:
            days = int(addons[addon]) - 3 # refresh tokens that expire this in the next three days
        except (ValueError, TypeError):
            days = 11  # OAuth2 spec's default refresh token expiry time is 14 days
        delta = relativedelta(days=days)
        Provider = look_up_provider(addon)
        if not Provider:
            logger.error('Unable to find Provider class for addon {}'.format(addon_short_name))
        else:
            main(delta, Provider, rate_limit, dry_run=dry_run)
