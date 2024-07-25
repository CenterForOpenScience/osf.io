import logging

from boaapi.boa_client import BoaClient, BoaException, BOA_API_ENDPOINT
from django.core.exceptions import ValidationError
from flask import request
from rest_framework import status as http_status

from addons.base import generic_views
from addons.boa.models import BoaProvider
from addons.boa.serializer import BoaSerializer
from addons.boa.tasks import submit_to_boa
from api.base.utils import waterbutler_api_url_for
from framework.auth.decorators import must_be_logged_in
from framework.celery_tasks.handlers import enqueue_task
from osf.models import ExternalAccount, AbstractNode
from osf.utils import permissions
from website import settings as osf_settings
from website.project.decorators import must_have_addon, must_have_permission

logger = logging.getLogger(__name__)


SHORT_NAME = 'boa'
FULL_NAME = 'Boa'

boa_account_list = generic_views.account_list(SHORT_NAME, BoaSerializer)
boa_import_auth = generic_views.import_auth(SHORT_NAME, BoaSerializer)
boa_deauthorize_node = generic_views.deauthorize_node(SHORT_NAME)
boa_get_config = generic_views.get_config(SHORT_NAME, BoaSerializer)


@must_be_logged_in
def boa_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list.
    This view expects `username` and `password` fields in the JSON body of the request.
    """

    username = request.json.get('username')
    password = request.json.get('password')
    try:
        boa_client = BoaClient(endpoint=BOA_API_ENDPOINT)
        boa_client.login(username, password)
        boa_client.close()
    except BoaException:
        return {'message': 'Boa Login failed.'}, http_status.HTTP_401_UNAUTHORIZED

    provider = BoaProvider(account=None, host=BOA_API_ENDPOINT, username=username, password=password)
    try:
        provider.account.save()
    except ValidationError:
        provider.account = ExternalAccount.objects.get(
            provider=provider.short_name,
            provider_id=f'{BOA_API_ENDPOINT}:{username}'.lower()
        )
        if provider.account.oauth_key != password:
            provider.account.oauth_key = password
            provider.account.save()
    except Exception:
        return {}

    user = auth.user
    if not user.external_accounts.filter(id=provider.account.id).exists():
        user.external_accounts.add(provider.account)

    user.get_or_add_addon('boa', auth=auth)
    user.save()
    return {}


@must_be_logged_in
@must_have_addon(SHORT_NAME, 'node')
@must_have_permission(permissions.WRITE)
def boa_submit_job(node_addon, **kwargs):

    req_params = request.json

    # Boa addon configuration
    provider = node_addon.external_account.provider_id
    parts = provider.rsplit(':', 1)
    host, username = parts[0], parts[1]
    password = node_addon.external_account.oauth_key

    # User and project
    user = kwargs['auth'].user
    user_guid = user._id
    project_guid = req_params['data']['nodeId']

    # Query file
    file_name = req_params['data']['name']
    file_size = req_params['data']['sizeInt']
    file_full_path = req_params['data']['materialized']
    file_download_url = req_params['data']['links']['download'].replace(osf_settings.WATERBUTLER_URL,
                                                                        osf_settings.WATERBUTLER_INTERNAL_URL)

    # Parent folder: project root is different from sub-folder
    is_addon_root = req_params['parent'].get('isAddonRoot', False)
    if is_addon_root:
        project_node = AbstractNode.load(project_guid)
        base_url = project_node.osfstorage_region.waterbutler_url
        parent_wb_url = waterbutler_api_url_for(project_guid, 'osfstorage', _internal=True, base_url=base_url)
        output_upload_url = f'{parent_wb_url}?kind=file'
    else:
        output_upload_url = req_params['parent']['links']['upload'].replace(osf_settings.WATERBUTLER_URL,
                                                                            osf_settings.WATERBUTLER_INTERNAL_URL)

    # Boa dataset
    dataset = req_params['dataset']

    # Send to task ``submit_to_boa``
    enqueue_task(submit_to_boa.s(host, username, password, user_guid, project_guid, dataset,
                                 file_name, file_size, file_full_path, file_download_url, output_upload_url))

    return {}
