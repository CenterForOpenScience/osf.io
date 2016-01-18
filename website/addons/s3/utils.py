import re
import httplib

from boto import exception
from boto.s3.connection import S3Connection
from boto.s3.connection import OrdinaryCallingFormat

from framework.exceptions import HTTPError
from website.addons.s3.settings import BUCKET_LOCATIONS


def connect_s3(access_key=None, secret_key=None, node_settings=None):
    """Helper to build an S3Connection object
    Can be used to change settings on all S3Connections
    See: CallingFormat
    """
    if node_settings is not None:
        if node_settings.external_account is not None:
            access_key, secret_key = node_settings.external_account.oauth_key, node_settings.external_account.oauth_secret
    connection = S3Connection(access_key, secret_key)
    return connection


def get_bucket_names(node_settings):
    try:
        buckets = connect_s3(node_settings=node_settings).get_all_buckets()
    except exception.NoAuthHandlerFound:
        raise HTTPError(httplib.FORBIDDEN)
    except exception.BotoServerError as e:
        raise HTTPError(e.status)

    return [bucket.name for bucket in buckets]


def validate_bucket_location(location):
    return location in BUCKET_LOCATIONS


def validate_bucket_name(name):
    validate_name = re.compile('^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$')
    return bool(validate_name.match(name))


def create_bucket(node_settings, bucket_name, location=''):
    return connect_s3(node_settings=node_settings).create_bucket(bucket_name, location=location)


def bucket_exists(access_key, secret_key, bucket_name):
    """Tests for the existance of a bucket and if the user
    can access it with the given keys
    """
    if not bucket_name:
        return False

    connection = connect_s3(access_key, secret_key)

    if bucket_name != bucket_name.lower():
        # Must use ordinary calling format for mIxEdCaSe bucket names
        # otherwise use the default as it handles bucket outside of the US
        connection.calling_format = OrdinaryCallingFormat()

    try:
        # Will raise an exception if bucket_name doesn't exist
        connect_s3(access_key, secret_key).head_bucket(bucket_name)
    except exception.S3ResponseError as e:
        if e.status not in (301, 302):
            return False
    return True


def can_list(access_key, secret_key):
    """Return whether or not a user can list
    all buckets accessable by this keys
    """
    # Bail out early as boto does not handle getting
    # Called with (None, None)
    if not (access_key and secret_key):
        return False

    try:
        connect_s3(access_key, secret_key).get_all_buckets()
    except exception.S3ResponseError:
        return False
    return True

def get_user_id(access_key, secret_key):
    """Returns a user's canonical user get_user_id
    according to S3, or None
    """
    if not (access_key and secret_key):
        return None

    try:
        return connect_s3(access_key, secret_key).get_canonical_user_id()
    except exception.S3ResponseError:
        return None
    return None
