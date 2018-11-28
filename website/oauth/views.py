# -*- coding: utf-8 -*-

import httplib as http

from flask import redirect

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError
from osf.models import ExternalAccount
from website.oauth.utils import get_service
from website.oauth.signals import oauth_complete
from requests.exceptions import ConnectionError


@must_be_logged_in
def oauth_disconnect(external_account_id, auth):
    account = ExternalAccount.load(external_account_id)
    user = auth.user

    if account is None:
        raise HTTPError(http.NOT_FOUND)

    if not user.external_accounts.filter(id=account.id).exists():
        raise HTTPError(http.FORBIDDEN)

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
def osf_oauth_callback(service_name, auth):
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

def oauth_callback(service_name):
    # OSFAdmin
    osfadmin_callback_url = osfadmin_oauth_callback(service_name)
    # if OAuth autherization failed on the OSFAdmin side,
    # consider it that the request was for OSF.
    if osfadmin_callback_url:
        try:
            return redirect(osfadmin_callback_url)
        except ConnectionError:
            pass
    # OSF
    return osf_oauth_callback(service_name)

def osfadmin_oauth_callback(service_name):
    from furl import furl
    import requests
    import flask
    from website.settings import ADMIN_INTERNAL_DOCKER_URL, ADMIN_URL
    f = furl(ADMIN_INTERNAL_DOCKER_URL)
    f.path = '/addons/oauth/callback/{}/'.format(service_name)
    f.args = flask.request.args.to_dict(flat=False)
    try:
        r = requests.get(f.url, headers=dict(flask.request.headers))
    except ConnectionError:
        return None
    if not r.ok:
        return None
    f = furl(ADMIN_URL)
    f.path = '/addons/oauth/complete/{}/'.format(service_name)
    return f.url
