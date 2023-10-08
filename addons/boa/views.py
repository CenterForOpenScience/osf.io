"""Views for the node settings page."""
# -*- coding: utf-8 -*-
import re
import time

from rest_framework import status as http_status

from django.core.exceptions import ValidationError
# from furl import furl
import requests
from flask import request
from framework.auth.decorators import must_be_logged_in

from addons.base import generic_views
from osf.models import ExternalAccount
from website.project.decorators import must_have_addon

from boaapi.boa_client import BoaClient, BOA_API_ENDPOINT
from boaapi.status import CompilerStatus, ExecutionStatus
from boaapi.util import BoaException

from addons.boa.models import BoaProvider
from addons.boa.serializer import BoaSerializer
#from addons.boa import settings

import logging
logger = logging.getLogger(__name__)


SHORT_NAME = 'boa'
FULL_NAME = 'Boa'

boa_account_list = generic_views.account_list(
    SHORT_NAME,
    BoaSerializer
)

boa_import_auth = generic_views.import_auth(
    SHORT_NAME,
    BoaSerializer
)

boa_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

## Config ##

@must_be_logged_in
def boa_add_user_account(auth, **kwargs):
    """
        Verifies new external account credentials and adds to user's list

        This view expects `username` and `password` fields in the JSON
        body of the request.
    """

    username = request.json.get('username')
    password = request.json.get('password')
    try:
        b = BoaClient(endpoint=BOA_API_ENDPOINT)
        b.login(username, password)
        b.close()
    except BoaException:
        return {
            'message': 'Boa Login failed.'
        }, http_status.HTTP_401_UNAUTHORIZED

    provider = BoaProvider(
        account=None, host=BOA_API_ENDPOINT, username=username, password=password
    )
    try:
        provider.account.save()
    except ValidationError:  # as vexc:
        # ... or get the old one
        provider.account = ExternalAccount.objects.get(
            provider=provider.short_name,
            provider_id='{}:{}'.format(BOA_API_ENDPOINT, username).lower()
        )
        if provider.account.oauth_key != password:
            provider.account.oauth_key = password
            provider.account.save()
    except Exception:  # as exc:
        return {}

    user = auth.user
    if not user.external_accounts.filter(id=provider.account.id).exists():
        user.external_accounts.add(provider.account)

    user.get_or_add_addon('boa', auth=auth)
    user.save()

    return {}

# @must_have_addon(SHORT_NAME, 'user')
# @must_have_addon(SHORT_NAME, 'node')
# def boa_folder_list(node_addon, user_addon, **kwargs):
#     """ Returns all the subsequent folders under the folder id passed.
#         Not easily generalizable due to `path` kwarg.
#     """
#     path = request.args.get('path')
#     return node_addon.get_folders(path=path)

def _set_folder(node_addon, folder, auth):
    node_addon.set_folder(folder['path'], auth=auth)
    node_addon.save()

boa_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    BoaSerializer,
    _set_folder
)

boa_get_config = generic_views.get_config(
    SHORT_NAME,
    BoaSerializer
)

@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
def boa_submit_job(node_addon, user_addon, **kwargs):

    provid = node_addon.external_account.provider_id
    parts = provid.rsplit(':', 1)
    host, username = parts[0], parts[1]
    password = node_addon.external_account.oauth_key
    boa = BoaClient(endpoint=host)
    boa.login(username, password)

    auth = kwargs['auth']
    user = auth.user
    cookie = user.get_or_create_cookie().decode()

    params = request.json
    attrs = params['data']
    links = attrs['links']
    download_url = links['download']
    download_url = download_url.replace('localhost', '192.168.168.167')
    # download_url += '?cookie=' + cookie
    resp = requests.get(download_url, params={'cookie': cookie})
    if resp.status_code != 200:
        logger.info('≥≥≥≥ boa_submit_job    failed to download from wb. resp:({}) '
                    'url:({})'.format(resp.status_code, download_url))
        boa.close()
        return {
            'message': 'Could not download source code from WaterButler, response:({})'.format(resp.status_code),
        }, http_status.HTTP_400_BAD_REQUEST

    query = resp.text

    job = boa.query(query, boa.get_dataset(params['dataset']))
    check = 1
    while job.is_running():
        job.refresh()
        logger.info('≥≥≥≥ boa_submit_job  {}: job ({}) still running, '
                    'waiting 10s...'.format(check, str(job.id)))
        check += 1
        time.sleep(10)

    output = None
    if job.compiler_status is CompilerStatus.ERROR:
        logger.info('≥≥≥≥ boa_submit_job    job ' + str(job.id) + ' had compile error')
        boa.close()
        return {
            'message': 'Boa job failed to compile.'
        }, http_status.HTTP_400_BAD_REQUEST
    elif job.exec_status is ExecutionStatus.ERROR:
        logger.info('≥≥≥≥ boa_submit_job    job ' + str(job.id) + ' had exec error')
        boa.close()
        return {
            'message': 'Boa job failed to compile.'
        }, http_status.HTTP_400_BAD_REQUEST

    output = job.output()
    logger.error('>>>>output:({}) isa:({})'.format(output, type(output)))
    upload_url = links['upload']
    upload_url = re.sub(r'\/[0123456789abcdef]+\?', '/?', upload_url)
    results_name = attrs['name'].replace('.boa', '_results.txt')
    upload_url = upload_url.replace('localhost', '192.168.168.167')
    up_resp = requests.put(upload_url, data=output,
                           params={'name': results_name, 'cookie': cookie})
    boa.close()

    if up_resp.status_code != 201:
        logger.info('≥≥≥≥ boa_submit_job    failed to upload results to wb. resp:({}) '
                    'url:({})'.format(up_resp.status_code, upload_url))
        return {
            'message': 'Could not upload results to WaterButler, response:({})'.format(up_resp.status_code),
        }, http_status.HTTP_400_BAD_REQUEST

    return {}
