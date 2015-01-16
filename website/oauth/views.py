from flask import redirect
from flask import request

from .models import get_service


def oauth_connect(service_name):
    service = get_service(service_name)

    return redirect(service.auth_url)


def oauth_callback(service_name):

    provider = get_service(service_name)

    provider.auth_callback(
        code=request.args.get('code'),
        state=request.args.get('state')
    )

    return repr(provider.account.to_storage())