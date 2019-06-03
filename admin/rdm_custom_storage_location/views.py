from django.http import HttpResponse
from scripts import refresh_addon_tokens
import hashlib
import json
SITE_KEY = 'rdm_custom_storage_location'

def external_acc_update(request, **kwargs):
    access_token = kwargs.get('access_token')
    if hashlib.sha512(SITE_KEY).hexdigest() == access_token.lower():
        refresh_addon_tokens.run_main({'googledrive': 14}, (5, 1), False)
    else:
        response_hash = {'state': 'fail', 'error': 'access forbidden'}
        response_json = json.dumps(response_hash)
        response = HttpResponse(response_json, content_type='application/json')
        return response
    return HttpResponse("Done")
