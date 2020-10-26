import logging
import httplib as http
import hmac
from hashlib import sha256
import json
from pprint import pformat as pf

from flask import request

from framework.exceptions import HTTPError

from addons.nextcloudinstitutions import settings, utils

logger = logging.getLogger(__name__)

NOTIFICATION_SECRETS = settings.NOTIFICATION_SECRETS

ENABLE_DEBUG = False

def DEBUG(msg):
    if ENABLE_DEBUG:
        logger.error('DEBUG: ' + msg)

def webhook_nextcloud_app():
    signature = request.headers.get('X-Nextcloud-File-Update-Notifications-Signature')
    if not signature:
        raise HTTPError(http.FORBIDDEN)
    DEBUG('signature: {}'.format(signature))

    if NOTIFICATION_SECRETS is None:
        logger.error('secrets is empty')
        raise HTTPError(http.INTERNAL_SERVER_ERROR)

    signature_valid = False
    for secret in NOTIFICATION_SECRETS:
        digest = hmac.new(secret, request.data, sha256).hexdigest()
        if hmac.compare_digest(signature.encode('utf-8'), digest):
            signature_valid = True
            break

    if signature_valid is False:
        logger.error('invalid signature')
        raise HTTPError(http.FORBIDDEN)

    data = json.loads(request.data)
    DEBUG(pf(data))

    provider_id = data.get('id')
    since = data.get('since')
    interval = data.get('min_interval')
    utils.celery_check_updated_files(provider_id, since, interval)

    return ''
