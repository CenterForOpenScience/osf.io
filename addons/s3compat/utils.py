import re
import httplib

from boto import exception
from boto.s3.connection import S3Connection, OrdinaryCallingFormat, NoHostProvided
from boto.s3.bucket import Bucket

from framework.exceptions import HTTPError
from addons.base.exceptions import InvalidAuthError, InvalidFolderError


class S3CompatConnection(S3Connection):
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None,
                 host=NoHostProvided, debug=0, https_connection_factory=None,
                 calling_format=None, path='/',
                 provider='aws', bucket_class=Bucket, security_token=None,
                 suppress_consec_slashes=True, anon=False,
                 validate_certs=None, profile_name=None):
        super(S3CompatConnection, self).__init__(aws_access_key_id,
                aws_secret_access_key,
                is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
                host=host,
                debug=debug, https_connection_factory=https_connection_factory,
                calling_format=calling_format,
                path=path, provider=provider, bucket_class=bucket_class,
                security_token=security_token, anon=anon,
                validate_certs=validate_certs, profile_name=profile_name)

    def _required_auth_capability(self):
        return ['s3']


def connect_s3compat(host=None, access_key=None, secret_key=None, node_settings=None):
    """Helper to build an S3CompatConnection object
    """
    if node_settings is not None:
        if node_settings.external_account is not None:
            host = node_settings.external_account.provider_id.split('\t')[0]
            access_key, secret_key = node_settings.external_account.oauth_key, node_settings.external_account.oauth_secret
    connection = S3CompatConnection(access_key, secret_key,
                                  calling_format=OrdinaryCallingFormat(),
                                  host=host)
    return connection


def get_bucket_names(node_settings):
    try:
        buckets = connect_s3compat(node_settings=node_settings).get_all_buckets()
    except exception.NoAuthHandlerFound:
        raise HTTPError(httplib.FORBIDDEN)
    except exception.BotoServerError as e:
        raise HTTPError(e.status)

    return [bucket.name for bucket in buckets]


def validate_bucket_name(name):
    """Make sure the bucket name conforms to Amazon's expectations as described at:
    http://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html#bucketnamingrules
    The laxer rules for US East (N. Virginia) are not supported.
    """
    label = '[a-z0-9]+(?:[a-z0-9\-]*[a-z0-9])?'
    validate_name = re.compile('^' + label + '(?:\\.' + label + ')*$')
    is_ip_address = re.compile('^[0-9]+(?:\.[0-9]+){3}$')
    return (
        len(name) >= 3 and len(name) <= 63 and bool(validate_name.match(name)) and not bool(is_ip_address.match(name))
    )


def create_bucket(node_settings, bucket_name):
    return connect_s3compat(node_settings=node_settings).create_bucket(bucket_name)


def bucket_exists(host, access_key, secret_key, bucket_name):
    """Tests for the existance of a bucket and if the user
    can access it with the given keys
    """
    if not bucket_name:
        return False

    connection = connect_s3compat(host, access_key, secret_key)

    if bucket_name != bucket_name.lower():
        # Must use ordinary calling format for mIxEdCaSe bucket names
        # otherwise use the default as it handles bucket outside of the US
        connection.calling_format = OrdinaryCallingFormat()

    try:
        # Will raise an exception if bucket_name doesn't exist
        connect_s3compat(host, access_key, secret_key).head_bucket(bucket_name)
    except exception.S3ResponseError as e:
        if e.status not in (301, 302):
            return False
    return True


def can_list(host, access_key, secret_key):
    """Return whether or not a user can list
    all buckets accessable by this keys
    """
    # Bail out early as boto does not handle getting
    # Called with (None, None)
    if not (host and access_key and secret_key):
        return False

    try:
        connect_s3compat(host, access_key, secret_key).get_all_buckets()
    except exception.S3ResponseError:
        return False
    return True

def get_user_info(host, access_key, secret_key):
    """Returns an S3 Compatible Storage User with .display_name and .id, or None
    """
    if not (access_key and secret_key):
        return None

    try:
        return connect_s3compat(host, access_key, secret_key).get_all_buckets().owner
    except exception.S3ResponseError:
        return None
    return None
