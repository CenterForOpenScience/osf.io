import httplib

from boto import exception
from django.core.exceptions import ValidationError
from flask import request

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from addons.base import generic_views
from addons.s3 import utils
from addons.s3.serializer import S3Serializer
from osf.models import ExternalAccount
from website.project.decorators import (
    must_have_addon, must_have_permission,
    must_be_addon_authorizer,
)

SHORT_NAME = 's3'
FULL_NAME = 'Amazon S3'

s3_account_list = generic_views.account_list(
    SHORT_NAME,
    S3Serializer
)

s3_import_auth = generic_views.import_auth(
    SHORT_NAME,
    S3Serializer
)

s3_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

s3_get_config = generic_views.get_config(
    SHORT_NAME,
    S3Serializer
)

def _set_folder(node_addon, folder, auth):
    folder_id = folder['id']
    node_addon.set_folder(folder_id, auth=auth)
    node_addon.save()

s3_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    S3Serializer,
    _set_folder
)

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def s3_folder_list(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
    """
    return node_addon.get_folders()

@must_be_logged_in
def s3_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""
    try:
        host = request.json['host']
        port = int(request.json['port'])
        encrypted = request.json['encrypted']
        access_key = request.json['access_key']
        secret_key = request.json['secret_key']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    if not (access_key and secret_key and host and port):
        return {
            'message': 'All the fields above are required.'
        }, httplib.BAD_REQUEST

    user_info = utils.get_user_info(
        host,
        port,
        access_key,
        secret_key,
        encrypted
    )
    import pdb
    pdb.set_trace()
    if not user_info:
        return {
            'message': ('Unable to access account.\n'
                'Check to make sure that the above credentials are valid, '
                'and that they have permission to list buckets.')
        }, httplib.BAD_REQUEST

    if not utils.can_list(
        host,
        port,
        access_key,
        secret_key,
        encrypted
    ):
        return {
            'message': ('Unable to list buckets.\n'
                'Listing buckets is required permission that can be changed via IAM')
        }, httplib.BAD_REQUEST

    account = None
    try:
        account = ExternalAccount(
            provider=SHORT_NAME,
            provider_name=FULL_NAME,
            host=host,
            port=port,
            encrypted=encrypted,
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
            provider_id=user_info.id,
            host=host,
            port=port
        )
        if (
            account.oauth_key != access_key or
            account.oauth_secret != secret_key or
            account.host != host or
            account.port != port or
            account.encrypted != encrypted
        ):
            account.oauth_key = access_key
            account.oauth_secret = secret_key
            account.host = host
            account.port = port
            account.encrypted = encrypted
            account.save()

    assert account is not None

    if not auth.user.external_accounts.filter(id=account.id).exists():
        auth.user.external_accounts.add(account)

    # Ensure S3 is enabled.
    auth.user.get_or_add_addon('s3', auth=auth)
    auth.user.save()

    return {}


@must_be_addon_authorizer(SHORT_NAME)
@must_have_addon('s3', 'node')
@must_have_permission('write')
def put_host(auth, node_addon, **kwargs):

    host = request.json.get('host', False)

    if not host:
        return {
            'message': 'No host was provided',
            'title': 'Invalid host',
        }, httplib.BAD_REQUEST

    node_addon.host = host
    node_addon.save()

    return {}


@must_be_addon_authorizer(SHORT_NAME)
@must_have_addon('s3', 'node')
@must_have_permission('write')
def create_bucket(auth, node_addon, **kwargs):
    bucket_name = request.json.get('bucket_name', '')
    bucket_location = request.json.get('bucket_location', '')

    if not utils.validate_bucket_name(bucket_name):
        return {
            'message': 'That bucket name is not valid.',
            'title': 'Invalid bucket name',
        }, httplib.BAD_REQUEST

    # Get location and verify it is valid
    if not utils.validate_bucket_location(bucket_location):
        return {
            'message': 'That bucket location is not valid.',
            'title': 'Invalid bucket location',
        }, httplib.BAD_REQUEST

    try:
        utils.create_bucket(node_addon, bucket_name, bucket_location)
    except exception.S3ResponseError as e:
        return {
            'message': e.message,
            'title': 'Problem connecting to S3',
        }, httplib.BAD_REQUEST
    except exception.S3CreateError as e:
        return {
            'message': e.message,
            'title': "Problem creating bucket '{0}'".format(bucket_name),
        }, httplib.BAD_REQUEST
    except exception.BotoClientError as e:  # Base class catchall
        return {
            'message': e.message,
            'title': 'Error connecting to S3',
        }, httplib.BAD_REQUEST

    return {}
