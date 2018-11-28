# -*- coding: utf-8 -*-

import httplib

from django.core.exceptions import ValidationError

from osf.models import ExternalAccount
from admin.rdm_addons.utils import get_rdm_addon_option
from addons.dataverse.models import DataverseProvider
from addons.dataverse import client

def add_account(json_request, institution_id, addon_name):
    host = json_request['host']
    api_token = json_request['api_token']

    provider = DataverseProvider()
    # check authentication
    client.connect_or_error(host, api_token)
    # acquire authentication account information
    try:
        provider.account = ExternalAccount(
            provider=provider.short_name,
            provider_name=provider.name,
            display_name=host,
            oauth_key=host,
            oauth_secret=api_token,
            provider_id=api_token,
        )
        provider.account.save()
    except ValidationError:
        # ... or get the old one
        provider.account = ExternalAccount.objects.get(
            provider=provider.short_name,
            provider_id=api_token
        )
    rdm_addon_option = get_rdm_addon_option(institution_id, addon_name)
    if not rdm_addon_option.external_accounts.filter(id=provider.account.id).exists():
        rdm_addon_option.external_accounts.add(provider.account)

    return {}, httplib.OK
