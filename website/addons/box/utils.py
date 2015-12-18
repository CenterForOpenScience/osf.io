# -*- coding: utf-8 -*-
import time
import logging
from datetime import datetime

from box import refresh_v2_token

from website.addons.box import settings

logger = logging.getLogger(__name__)


def refresh_oauth_key(external_account, force=False):
    """If necessary, refreshes the oauth key associated with
    the external account.
    """
    if external_account.expires_at is None and not force:
        return

    if force or (external_account.expires_at - datetime.utcnow()).total_seconds() < settings.REFRESH_TIME:
        key = refresh_v2_token(settings.BOX_KEY, settings.BOX_SECRET, external_account.refresh_token)

        external_account.oauth_key = key['access_token']
        external_account.refresh_token = key['refresh_token']
        external_account.expires_at = datetime.utcfromtimestamp(time.time() + key['expires_in'])
        external_account.save()
