# -*- coding: utf-8 -*-

from future.moves.urllib.parse import urlparse
from rest_framework import status as http_status

from django.core.exceptions import ValidationError
from addons.weko.apps import SHORT_NAME

from osf.models import ExternalAccount
from admin.rdm_addons.utils import get_rdm_addon_option


OAUTH_CLIENT_SHORT_LENGTH = 4


def add_account(json_request, institution_id, addon_name):
    display_name_ = json_request['display_name']
    url = json_request['url']
    oauth_client_id = json_request['oauth_client_id']
    oauth_client_secret = json_request['oauth_client_secret']

    hostname = urlparse(url).hostname
    oauth_client_short_id = oauth_client_id[:OAUTH_CLIENT_SHORT_LENGTH]
    display_name = f'{url}#{display_name_}'
    provider_id = f'{hostname}.{oauth_client_short_id}'
    try:
        account = ExternalAccount(
            provider=SHORT_NAME,
            provider_name=SHORT_NAME,
            display_name=display_name,
            oauth_key=oauth_client_id,
            oauth_secret=oauth_client_secret,
            provider_id=provider_id,
        )
        account.save()
    except ValidationError:
        # ... or get the old one
        account = ExternalAccount.objects.get(
            provider=SHORT_NAME,
            provider_id=provider_id
        )
        account.display_name = display_name
        account.oauth_key = oauth_client_id
        account.oauth_secret = oauth_client_secret
        account.save()
    rdm_addon_option = get_rdm_addon_option(institution_id, addon_name)
    if not rdm_addon_option.external_accounts.filter(id=account.id).exists():
        rdm_addon_option.external_accounts.add(account)

    return {}, http_status.HTTP_200_OK
