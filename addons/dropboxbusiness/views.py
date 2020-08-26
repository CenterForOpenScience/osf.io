"""Views fo the node settings page."""
# -*- coding: utf-8 -*-

import logging
from rest_framework import status as http_status
import hmac
from hashlib import sha256
import json
from pprint import pformat as pf

from flask import request, Response

from addons.dropboxbusiness import settings, utils
from framework.exceptions import HTTPError

logger = logging.getLogger(__name__)

# add a URL into Webhook URIs in App console of Team member file access.
# URL format:
#   https://(web server hostname)/api/v1/addons/dropboxbusiness/webhook/

APP_SECRET = settings.DROPBOX_BUSINESS_FILEACCESS_SECRET

ENABLE_DEBUG = False

def DEBUG(msg):
    if ENABLE_DEBUG:
        logger.error('DEBUG: ' + msg)

def webhook_challenge():
    """Respond to the Dropbox webhook challenge (GET request) by echoing
    back the challenge parameter.
    """
    resp = Response(request.args.get('challenge'))
    resp.headers['Content-Type'] = 'text/plain'
    resp.headers['X-Content-Type-Options'] = 'nosniff'

    return resp

def webhook_post():
    """Receive a list of changed team IDs from Dropbox Business Apps and
    process each.
    """
    # Make sure this is a valid request from Dropbox
    signature = request.headers.get('X-Dropbox-Signature')
    if not signature:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    if not hmac.compare_digest(
            signature.encode('utf-8'),
            hmac.new(APP_SECRET, request.data, sha256).hexdigest()):
        logger.error('invalid signature')
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    data = json.loads(request.data)
    if ENABLE_DEBUG:
        s = pf(data)
        DEBUG(s)

    team_ids = []
    list_folder = data.get('list_folder')
    if list_folder:
        teams = list_folder.get('teams')
        if teams:
            for dbtid in teams.keys():
                DEBUG('dbtid={}'.format(dbtid))
                team_ids.append(dbtid)
    utils.celery_check_and_add_timestamp.delay(team_ids)

    return ''
