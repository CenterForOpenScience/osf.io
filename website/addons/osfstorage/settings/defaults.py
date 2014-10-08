# -*- coding: utf-8 -*-

import hashlib


UPLOAD_SERVICE_URL = 'changeme'

# HMAC options
SIGNATURE_HEADER_KEY = 'X-Signature'
URLS_HMAC_SECRET = 'changeme'
URLS_HMAC_DIGEST = hashlib.sha1
WEBHOOK_HMAC_SECRET = 'changeme'
WEBHOOK_HMAC_DIGEST = hashlib.sha1

