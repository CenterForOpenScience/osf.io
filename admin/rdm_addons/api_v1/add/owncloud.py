# -*- coding: utf-8 -*-

from __future__ import absolute_import
import httplib

from furl import furl
import requests
from django.core.exceptions import ValidationError

from osf.models import ExternalAccount
from admin.rdm_addons.utils import get_rdm_addon_option

import owncloud
from addons.owncloud.models import OwnCloudProvider
#from addons.owncloud.serializer import OwnCloudSerializer
from addons.owncloud import settings


def add_account(json_request, institution_id, addon_name):
    """
        Verifies new external account credentials and adds to user's list

        This view expects `host`, `username` and `password` fields in the JSON
        body of the request.
    """

    # Ensure that ownCloud uses https
    host_url = json_request['host']
    host = furl()
    host.host = host_url.rstrip('/').replace('https://', '').replace('http://', '')
    host.scheme = 'https'

    username = json_request['username']
    password = json_request['password']

    try:
        oc = owncloud.Client(host.url, verify_certs=settings.USE_SSL)
        oc.login(username, password)
        oc.logout()
    except requests.exceptions.ConnectionError:
        return {
            'message': 'Invalid ownCloud server.' + host.url
        }, httplib.BAD_REQUEST
    except owncloud.owncloud.HTTPResponseError:
        return {
            'message': 'ownCloud Login failed.'
        }, httplib.UNAUTHORIZED

    provider = OwnCloudProvider(account=None, host=host.url,
                            username=username, password=password)
    try:
        provider.account.save()
    except ValidationError:
        # ... or get the old one
        provider.account = ExternalAccount.objects.get(
            provider=provider.short_name,
            provider_id='{}:{}'.format(host.url, username).lower()
        )
        if provider.account.oauth_key != password:
            provider.account.oauth_key = password
            provider.account.save()

    rdm_addon_option = get_rdm_addon_option(institution_id, addon_name)
    if not rdm_addon_option.external_accounts.filter(id=provider.account.id).exists():
        rdm_addon_option.external_accounts.add(provider.account)

    return {}, httplib.OK
