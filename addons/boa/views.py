import logging
import re

from boaapi.boa_client import BoaClient, BoaException, BOA_API_ENDPOINT
from django.core.exceptions import ValidationError
from flask import request
from rest_framework import status as http_status

from addons.base import generic_views
from addons.boa.models import BoaProvider
from addons.boa.serializer import BoaSerializer
from addons.boa.tasks import submit_to_boa
from framework.auth.decorators import must_be_logged_in
from framework.celery_tasks.handlers import enqueue_task
from osf.models import ExternalAccount
from website import settings as osf_settings
from website.project.decorators import must_have_addon

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


@must_be_logged_in
@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
def boa_submit_job(node_addon, user_addon, **kwargs):

    provider = node_addon.external_account.provider_id
    parts = provider.rsplit(':', 1)
    host, username = parts[0], parts[1]
    password = node_addon.external_account.oauth_key
    # user_guid = kwargs['auth'].user._id
    user = kwargs['auth'].user
    cookie_value = user.get_or_create_cookie().decode()
    params = request.json
    dataset = params['dataset']
    attrs = params['data']
    file_name = attrs['name']
    links = attrs['links']
    download_url = links['download']
    download_url = download_url.replace(osf_settings.WATERBUTLER_URL, osf_settings.WATERBUTLER_INTERNAL_URL)
    upload_url = links['upload']
    upload_url = re.sub(r'\/[0123456789abcdef]+\?', '/?', upload_url)
    upload_url = upload_url.replace(osf_settings.WATERBUTLER_URL, osf_settings.WATERBUTLER_INTERNAL_URL)
    logger.info(attrs)
    enqueue_task(submit_to_boa.s(
        host, username, password, cookie_value, dataset, file_name, download_url, upload_url
    ))
