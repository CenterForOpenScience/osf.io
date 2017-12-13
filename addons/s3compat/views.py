import httplib

from boto import exception
from django.core.exceptions import ValidationError
from flask import request

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from addons.base import generic_views
from addons.s3compat import utils
from addons.s3compat.serializer import S3CompatSerializer
import addons.s3compat.settings as settings
from osf.models import ExternalAccount
from website.project.decorators import (
    must_have_addon, must_have_permission,
    must_be_addon_authorizer,
)


SHORT_NAME = 's3compat'
FULL_NAME = 'S3 Compatible Storage'

s3compat_account_list = generic_views.account_list(
    SHORT_NAME,
    S3CompatSerializer
)

s3compat_import_auth = generic_views.import_auth(
    SHORT_NAME,
    S3CompatSerializer
)

s3compat_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

s3compat_get_config = generic_views.get_config(
    SHORT_NAME,
    S3CompatSerializer
)

def _set_folder(node_addon, folder, auth):
    folder_id = folder['id']
    node_addon.set_folder(folder_id, auth=auth)
    node_addon.save()

s3compat_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    S3CompatSerializer,
    _set_folder
)

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def s3compat_folder_list(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
    """
    return node_addon.get_folders()

@must_be_logged_in
def s3compat_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""
    try:
        host = request.json['host']
        access_key = request.json['access_key']
        secret_key = request.json['secret_key']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    if not (host and access_key and secret_key):
        return {
            'message': 'All the fields above are required.'
        }, httplib.BAD_REQUEST
    if host not in [s['host'] for s in settings.AVAILABLE_SERVICES]:
        return {
            'message': 'The host is not available.'
        }, httplib.BAD_REQUEST

    user_info = utils.get_user_info(host, access_key, secret_key)
    if not user_info:
        return {
            'message': ('Unable to access account.\n'
                'Check to make sure that the above credentials are valid, '
                'and that they have permission to list buckets.')
        }, httplib.BAD_REQUEST

    if not utils.can_list(host, access_key, secret_key):
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
            provider_id='{}\t{}'.format(host, user_info.id),
            display_name=user_info.display_name,
        )
        account.save()
    except ValidationError:
        # ... or get the old one
        account = ExternalAccount.objects.get(
            provider=SHORT_NAME,
            provider_id='{}\t{}'.format(host, user_info.id)
        )
        if account.oauth_key != access_key or account.oauth_secret != secret_key:
            account.oauth_key = access_key
            account.oauth_secret = secret_key
            account.save()
    assert account is not None

    if not auth.user.external_accounts.filter(id=account.id).exists():
        auth.user.external_accounts.add(account)

    # Ensure S3 Compatible Storage is enabled.
    auth.user.get_or_add_addon('s3compat', auth=auth)
    auth.user.save()

    return {}


@must_be_addon_authorizer(SHORT_NAME)
@must_have_addon('s3compat', 'node')
@must_have_permission('write')
def s3compat_create_bucket(auth, node_addon, **kwargs):
    bucket_name = request.json.get('bucket_name', '')

    if not utils.validate_bucket_name(bucket_name):
        return {
            'message': 'That bucket name is not valid.',
            'title': 'Invalid bucket name',
        }, httplib.BAD_REQUEST

    try:
        utils.create_bucket(node_addon, bucket_name)
    except exception.S3ResponseError as e:
        return {
            'message': e.message,
            'title': 'Problem connecting to S3 Compatible Storage',
        }, httplib.BAD_REQUEST
    except exception.S3CreateError as e:
        return {
            'message': e.message,
            'title': "Problem creating bucket '{0}'".format(bucket_name),
        }, httplib.BAD_REQUEST
    except exception.BotoClientError as e:  # Base class catchall
        return {
            'message': e.message,
            'title': 'Error connecting to S3 Compatible Storage',
        }, httplib.BAD_REQUEST

    return {}
