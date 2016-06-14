from . import sign_payload

from django.http import HttpResponseRedirect

from rest_framework.exceptions import AuthenticationFailed

from framework.auth import cas

from api.base.utils import get_user_auth
from api.base.views import JSONAPIBaseView

from website import settings

from furl import furl
import base64
import urllib
import hashlib
import hmac

class SSOView(JSONAPIBaseView):
    view_name = 'sso-view'
    view_category = 'sso'

    # NOTE: directing a user to DISCOURSE/session/sso should trigger the sso process
    # for automatic sso login.

    # send DELETE /session/username/ to log them out

    def get(self, request):
        auth = get_user_auth(request)
        user = request.user
        sso_secret = settings.DISCOURSE_SSO_SECRET

        if not auth.logged_in:
            #sso_url = furl(settings.DISCOURSE_SERVER_URL).join('/session/sso')
            return HttpResponseRedirect(cas.get_login_url(settings.HOST, auto=True))

        encoded_payload = request.GET.get('sso', '')
        payload = base64.b64decode(encoded_payload)
        try:
            payload_dict = {urllib.unquote(item[0]): urllib.unquote(item[1])
                            for item in
                            [item.split('=') for item in payload.split('&')]}
        except IndexError:
            raise AuthenticationFailed

        nonce = payload_dict['nonce']
        signature = request.GET.get('sig', '')

        payload_hash = hmac.new(sso_secret, encoded_payload, hashlib.sha256).hexdigest()

        if payload_hash != signature:
            raise AuthenticationFailed

        return_payload = {'nonce': nonce,
                          'email': user.username,
                          'external_id': user._id,
                          'username': user._id,
                          'name': user.fullname,
                          'avatar_url': user.profile_image_url()}

        return_url = furl(settings.DISCOURSE_SERVER_URL).join('/session/sso_login')
        return_url.args = sign_payload(return_payload)

        return HttpResponseRedirect(return_url.url)
