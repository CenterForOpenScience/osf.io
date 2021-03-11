import logging
from rest_framework import status as http_status
import hmac
from hashlib import sha256
import json
from pprint import pformat as pf

from flask import request

from framework.exceptions import HTTPError

from osf.models.external import ExternalAccount
from osf.models.rdm_addons import RdmAddonOption
from addons.nextcloudinstitutions import utils, apps, KEYNAME_NOTIFICATION_SECRET

logger = logging.getLogger(__name__)

SHORT_NAME = apps.SHORT_NAME

ENABLE_DEBUG = False

def DEBUG(msg):
    if ENABLE_DEBUG:
        logger.error('DEBUG: ' + msg)

def webhook_nextcloud_app():
    signature = request.headers.get('X-Nextcloud-File-Upload-Notification-Signature')
    if not signature:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    DEBUG('signature: {}'.format(signature))

    try:
        data = json.loads(request.data)
        provider_id = data.get('id')
    except Exception:
        logger.error('provider_id not found')
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)

    try:
        ea = ExternalAccount.objects.get(
            provider=SHORT_NAME, provider_id=provider_id)
        opt = RdmAddonOption.objects.get(
            provider=SHORT_NAME, external_accounts=ea)
    except Exception:
        logger.error('provider not found')
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)

    if opt.extended is None:
        logger.error('secret not found')
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)

    secret = opt.extended.get(KEYNAME_NOTIFICATION_SECRET)
    if secret is None:
        logger.error('secrets is empty')
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)

    digest = hmac.new(secret.encode(), request.data, sha256).hexdigest()
    if not hmac.compare_digest(signature.encode('utf-8'), digest):
        logger.error('invalid signature')
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)

    DEBUG(pf(data))

    since = data.get('since')
    interval = data.get('min_interval')
    utils.celery_check_updated_files.delay(provider_id, since, interval)

    return ''
