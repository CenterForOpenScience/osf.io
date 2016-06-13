from website import settings

import base64
import urllib
import hashlib
import hmac

def sign_payload(payload):
    sso_secret = settings.DISCOURSE_SSO_SECRET

    encoded_return_64 = base64.b64encode(urllib.urlencode(payload))
    return_signature = hmac.new(sso_secret, encoded_return_64, hashlib.sha256).hexdigest()
    return {
        'sso': encoded_return_64,
        'sig': return_signature
    }
