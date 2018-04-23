# -*- coding: utf-8 -*-

import httplib

from django.core.exceptions import ValidationError

from framework.exceptions import HTTPError
from osf.models import RdmAddonOption, ExternalAccount
from admin.rdm_addons.utils import get_rdm_addon_option
from addons.s3.views import SHORT_NAME, FULL_NAME
from addons.s3.utils import get_user_info, can_list


def add_account(json_request, institution_id, addon_name):
    try:
        access_key = json_request['access_key']
        secret_key = json_request['secret_key']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    if not (access_key and secret_key):
        return {
            'message': 'All the fields above are required.'
        }, httplib.BAD_REQUEST

    user_info = get_user_info(access_key, secret_key)
    if not user_info:
        return {
            'message': ('Unable to access account.\n'
                'Check to make sure that the above credentials are valid, '
                'and that they have permission to list buckets.')
        }, httplib.BAD_REQUEST

    if not can_list(access_key, secret_key):
        return {
            'message': ('Unable to list buckets.\n'
                'Listing buckets is required permission that can be changed via IAM')
        }, httplib.BAD_REQUEST

    account = None
    try:
        account = ExternalAccount(
            provider=SHORT_NAME,
            provider_name=FULL_NAME,
            oauth_key=access_key,
            oauth_secret=secret_key,
            provider_id=user_info.id,
            display_name=user_info.display_name,
        )
        account.save()
    except ValidationError:
        # ... or get the old one
        account = ExternalAccount.objects.get(
            provider=SHORT_NAME,
            provider_id=user_info.id
        )
        if account.oauth_key != access_key or account.oauth_secret != secret_key:
            account.oauth_key = access_key
            account.oauth_secret = secret_key
            account.save()
    assert account is not None

    rdm_addon_option = get_rdm_addon_option(institution_id, addon_name)
    if not rdm_addon_option.external_accounts.filter(id=account.id).exists():
        rdm_addon_option.external_accounts.add(account)

    return {}, httplib.OK