# -*- coding: utf-8 -*-

import httplib as http

from flask import redirect

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError
from website.oauth.models import ExternalAccount
from website.oauth.utils import get_service
from website.oauth.signals import oauth_complete

@must_be_logged_in
def oauth_disconnect(external_account_id, auth):
    account = ExternalAccount.load(external_account_id)
    user = auth.user

    if account is None:
        raise HTTPError(http.NOT_FOUND)

    if account not in user.external_accounts:
        raise HTTPError(http.FORBIDDEN)

    # iterate AddonUserSettings for addons
    for user_settings in user.get_oauth_addons():
        user_settings.revoke_oauth_access(account)
        user_settings.save()

    # ExternalAccount.remove_one(account)
    # # only after all addons have been dealt with can we remove it from the user
    user.external_accounts.remove(account)
    user.save()

@must_be_logged_in
def oauth_connect(service_name, auth):
    service = get_service(service_name)

    return redirect(service.auth_url)


@must_be_logged_in
def oauth_callback(service_name, auth):
    user = auth.user
    provider = get_service(service_name)

    # Retrieve permanent credentials from provider
    if not provider.auth_callback(user=user):
        return {}

    if provider.account not in user.external_accounts:
        user.external_accounts.append(provider.account)
        user.save()

    oauth_complete.send(provider, account=provider.account, user=user)

    return {}
