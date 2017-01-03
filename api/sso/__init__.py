import base64
import hashlib
import hmac
import urllib

from website import settings

# http://stackoverflow.com/questions/6480723/urllib-urlencode-doesnt-like-unicode-values-how-about-this-workaround
# John Machin
def _utf8_encode_dict(in_dict):
    out_dict = {}
    for k, v in in_dict.iteritems():
        if isinstance(v, unicode):
            v = v.encode('utf-8')
        elif isinstance(v, str):
            # Throw an error if the string is not valid utf8
            v.decode('utf-8')
        out_dict[k] = v
    return out_dict

def sign_payload(payload):
    sso_secret = settings.DISCOURSE_SSO_SECRET

    encoded_return_64 = base64.b64encode(urllib.urlencode(_utf8_encode_dict(payload)))
    return_signature = hmac.new(sso_secret, encoded_return_64, hashlib.sha256).hexdigest()
    return {
        'sso': encoded_return_64,
        'sig': return_signature
    }
