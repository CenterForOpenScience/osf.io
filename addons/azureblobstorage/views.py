import httplib

from azure.common import AzureHttpError
from flask import request
from modularodm import Q
from modularodm.storage.base import KeyExistsException

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from addons.base import generic_views
from addons.azureblobstorage import utils
from addons.azureblobstorage.provider import AzureBlobStorageProvider
from addons.azureblobstorage.serializer import AzureBlobStorageSerializer
from website.oauth.models import ExternalAccount
from website.project.decorators import (
    must_have_addon, must_have_permission,
    must_be_addon_authorizer,
)

SHORT_NAME = 'azureblobstorage'
FULL_NAME = 'Azure Blob Storage'

azureblobstorage_account_list = generic_views.account_list(
    SHORT_NAME,
    AzureBlobStorageSerializer
)

azureblobstorage_import_auth = generic_views.import_auth(
    SHORT_NAME,
    AzureBlobStorageSerializer
)

azureblobstorage_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

azureblobstorage_get_config = generic_views.get_config(
    SHORT_NAME,
    AzureBlobStorageSerializer
)

def _set_folder(node_addon, folder, auth):
    folder_id = folder['id']
    node_addon.set_folder(folder_id, auth=auth)
    node_addon.save()

azureblobstorage_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    AzureBlobStorageSerializer,
    _set_folder
)

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def azureblobstorage_folder_list(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
    """
    return node_addon.get_folders()

@must_be_logged_in
def azureblobstorage_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""
    try:
        access_key = request.json['access_key']
        secret_key = request.json['secret_key']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    if not (access_key and secret_key):
        return {
            'message': 'All the fields above are required.'
        }, httplib.BAD_REQUEST

    user_info = utils.get_user_info(access_key, secret_key)
    if not user_info:
        return {
            'message': ('Unable to access account.\n'
                'Check to make sure that the above credentials are valid, '
                'and that they have permission to list buckets.')
        }, httplib.BAD_REQUEST

    if not utils.can_list(access_key, secret_key):
        return {
            'message': ('Unable to list buckets.\n'
                'Listing buckets is required permission that can be changed via IAM')
        }, httplib.BAD_REQUEST

    try:
        account = ExternalAccount(
            provider=SHORT_NAME,
            provider_name=FULL_NAME,
            oauth_key=access_key,
            oauth_secret=secret_key,
            provider_id=user_info['id'],
            display_name=user_info['display_name'],
        )
        account.save()
    except KeyExistsException:
        # ... or get the old one
        account = ExternalAccount.find_one(
            Q('provider', 'eq', SHORT_NAME) &
            Q('provider_id', 'eq', user_info['id'])
        )
    assert account is not None

    if account not in auth.user.external_accounts:
        auth.user.external_accounts.append(account)

    # Ensure Azure Blob Storage is enabled.
    auth.user.get_or_add_addon('azureblobstorage', auth=auth)
    auth.user.save()

    return {}


@must_be_addon_authorizer(SHORT_NAME)
@must_have_addon('azureblobstorage', 'node')
@must_have_permission('write')
def azureblobstorage_create_container(auth, node_addon, **kwargs):
    bucket_name = request.json.get('bucket_name', '')

    if not utils.validate_bucket_name(bucket_name):
        return {
            'message': 'That container name is not valid.',
            'title': 'Invalid container name',
        }, httplib.BAD_REQUEST

    try:
        utils.create_container(node_addon, bucket_name)
    except AzureHttpError as e:
        return {
            'message': e.message,
            'title': 'Problem connecting to Azure Blob Storage',
        }, httplib.BAD_REQUEST

    return {}
