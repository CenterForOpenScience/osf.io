import httplib

from boto import exception
from flask import request
from modularodm import Q
from modularodm.storage.base import KeyExistsException

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from website.addons.base import generic_views
from website.addons.s3 import utils
from website.addons.s3.serializer import S3Serializer
from website.oauth.models import ExternalAccount
from website.project.decorators import (
    must_have_addon, must_have_permission,
    must_not_be_registration, must_be_addon_authorizer,
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

def _get_buckets(node_addon, folder_id=None):
    """Used by generic_view `folder_list` to fetch a list of buckets.
    `folder_id` required by generic, but not actually used"""
    return {
        'buckets': utils.get_bucket_names(node_addon)
    }

s3_folder_list = generic_views.folder_list(
    SHORT_NAME,
    FULL_NAME,
    _get_buckets
)

s3_root_folder = generic_views.root_folder(
    SHORT_NAME
)

@must_be_logged_in
def s3_add_user_account(auth, **kwargs):
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
    except KeyExistsException:
        # ... or get the old one
        account = ExternalAccount.find_one(
            Q('oauth_key', 'eq', access_key) &
            Q('oauth_secret', 'eq', secret_key)
        )
    assert account is not None

    if account not in auth.user.external_accounts:
        auth.user.external_accounts.append(account)

    # Ensure S3 is enabled.
    auth.user.get_or_add_addon('s3', auth=auth)
    auth.user.save()

    return {}


@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
@must_not_be_registration
def s3_set_config(node, auth, user_addon, node_addon, **kwargs):
    """Saves selected bucket to node settings."""
    # Fail if user settings not authorized
    if not user_addon.has_auth:
        raise HTTPError(httplib.UNAUTHORIZED)

    # If authorized, only owner can change settings
    if node_addon.has_auth and node_addon.user_settings.owner != auth.user:
        raise HTTPError(httplib.FORBIDDEN)

    # Claiming the node settings
    if not node_addon.user_settings:
        node_addon.user_settings = user_addon

    bucket = request.json.get('s3_bucket', '')

    if not utils.bucket_exists(node_addon.external_account.oauth_key, node_addon.external_account.oauth_secret, bucket):
        error_message = ('We are having trouble connecting to that bucket. '
                         'Try a different one.')
        return {'message': error_message}, httplib.BAD_REQUEST

    if bucket != node_addon.bucket:

        # Update node settings and log
        node_addon.set_folder(bucket, auth)

    return S3Serializer().serialize_settings(node_addon, auth.user)

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

    return {
        'buckets': utils.get_bucket_names(node_addon)
    }
