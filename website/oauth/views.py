from rest_framework import status as http_status
import waffle
import requests
from urllib.parse import (
    urlencode,
    urlparse,
    urlunparse,
)

from flask import redirect, request

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError
from osf.models import ExternalAccount
from osf import features
from website.oauth.utils import get_service
from website.oauth.signals import oauth_complete
from website.settings import GRAVYVALET_URL

@must_be_logged_in
def oauth_disconnect(external_account_id, auth):
    account = ExternalAccount.load(external_account_id)
    user = auth.user

    if account is None:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

    if not user.external_accounts.filter(id=account.id).exists():
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)

    # iterate AddonUserSettings for addons
    for user_settings in user.get_oauth_addons():
        if user_settings.oauth_provider.short_name == account.provider:
            user_settings.revoke_oauth_access(account)
            user_settings.save()

    # ExternalAccount.delete(account)
    # # only after all addons have been dealt with can we remove it from the user
    user.external_accounts.remove(account)
    user.save()

@must_be_logged_in
def oauth_connect(service_name, auth):
    service = get_service(service_name)

    return redirect(service.auth_url)


@must_be_logged_in
def oauth_callback(service_name, auth):
    if waffle.flag_is_active(request, features.ENABLE_GV):
        _forward_to_addon_service()
        return {}

    user = auth.user
    provider = get_service(service_name)

    # Retrieve permanent credentials from provider
    if not provider.auth_callback(user=user):
        return {}

    if provider.account and not user.external_accounts.filter(id=provider.account.id).exists():
        user.external_accounts.add(provider.account)
        user.save()

    oauth_complete.send(provider, account=provider.account, user=user)

    return {}

def _forward_to_addon_service():
    code = request.args.get('code')
    state = request.args.get('state')
    query_params = {
        'code': code,
        'state': state,
    }
    gv_url = urlunparse(urlparse(GRAVYVALET_URL)._replace(path='/v1/oauth/callback', query=urlencode(query_params)))
    requests.get(gv_url)
