from flask import redirect
from flask import request

from framework.auth.decorators import must_be_logged_in
from .utils import get_service


@must_be_logged_in
def oauth_connect(service_name, auth):
    service = get_service(service_name)

    return redirect(service.auth_url)


@must_be_logged_in
def oauth_callback(service_name, auth):
    user = auth.user
    provider = get_service(service_name)

    # Retrieve permanent credentials from provider
    provider.auth_callback(user=user)

    if provider.account not in user.external_accounts:
        user.external_accounts.append(provider.account)
        user.save()

    return repr(provider.account.to_storage())