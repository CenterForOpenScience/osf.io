import re
from rest_framework import status as http_status

from boto import exception
from boto.s3.connection import NoHostProvided
from boto.s3.bucket import Bucket

import boto3
import botocore
from botocore.exceptions import ClientError
# from boto3 import exception
import addons.s3compatb3.settings as settings

from framework.exceptions import HTTPError
from addons.base.exceptions import InvalidAuthError, InvalidFolderError


# class S3CompatB3Connection(S3Connection):
#     def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
#                  is_secure=True, port=None, proxy=None, proxy_port=None,
#                  proxy_user=None, proxy_pass=None,
#                  host=NoHostProvided, debug=0, https_connection_factory=None,
#                  calling_format=None, path='/',
#                  provider='aws', bucket_class=Bucket, security_token=None,
#                  suppress_consec_slashes=True, anon=False,
#                  validate_certs=None, profile_name=None):
#         super(S3CompatB3Connection, self).__init__(aws_access_key_id,
#                 aws_secret_access_key,
#                 is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
#                 host=host,
#                 debug=debug, https_connection_factory=https_connection_factory,
#                 calling_format=calling_format,
#                 path=path, provider=provider, bucket_class=bucket_class,
#                security_token=security_token, anon=anon,
#                 validate_certs=validate_certs, profile_name=profile_name)
#
#     def _required_auth_capability(self):
#         return ['s3']
class S3CompatB3Connection:
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None,
                 host=NoHostProvided, debug=0, https_connection_factory=None,
                 calling_format=None, path='/',
                 provider='aws', bucket_class=Bucket, security_token=None,
                 suppress_consec_slashes=True, anon=False,
                 validate_certs=None, profile_name=None):
        port = 443
        m = re.match(r'^(.+)\:([0-9]+)$', host)
        if m is not None:
            host = m.group(1)
            port = int(m.group(2))
        region = ''
        if host.endswith('.oraclecloud.com'):
            region = host.split('.')[-3]
        url = ('https://' if port == 443 else 'http://') + host
        self.conn = boto3.resource(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region,
            endpoint_url=url
        )


def connect_s3compatb3(host=None, access_key=None, secret_key=None, node_settings=None):
    """Helper to build an S3CompatB3Connection object
    """
    if node_settings is not None:
        if node_settings.external_account is not None:
            host = node_settings.external_account.provider_id.split('\t')[0]
            access_key, secret_key = node_settings.external_account.oauth_key, node_settings.external_account.oauth_secret
    port = 443
    m = re.match(r'^(.+)\:([0-9]+)$', host)
    if m is not None:
        host = m.group(1)
        port = int(m.group(2))
    region = ''
    if host.endswith('.oraclecloud.com'):
        region = host.split('.')[-3]
    url = ('https://' if port == 443 else 'http://') + host
    return boto3.resource(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        endpoint_url=url
    )


def get_bucket_names(node_settings):
    try:
        buckets = connect_s3compatb3(node_settings=node_settings).buckets.all()
    except exception.NoAuthHandlerFound:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    except exception.BotoServerError as e:
        raise HTTPError(e.status)

    return [bucket.name for bucket in buckets]


def find_service_by_host(host):
    services = [s for s in settings.AVAILABLE_SERVICES if s['host'] == host]
    if len(services) == 0:
        raise KeyError(host)
    return services[0]


def validate_bucket_location(node_settings, location):
    if location == '':
        return True
    host = node_settings.external_account.provider_id.split('\t')[0]
    service = find_service_by_host(host)
    return location in service['bucketLocations']


def validate_bucket_name(name):
    """Make sure the bucket name conforms to Amazon's expectations as described at:
    http://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html#bucketnamingrules
    The laxer rules for US East (N. Virginia) are not supported.
    """
    label = r'[a-z0-9]+(?:[a-z0-9\-]*[a-z0-9])?'
    validate_name = re.compile('^' + label + '(?:\\.' + label + ')*$')
    is_ip_address = re.compile(r'^[0-9]+(?:\.[0-9]+){3}$')
    return (
        len(name) >= 3 and len(name) <= 63 and bool(validate_name.match(name)) and not bool(is_ip_address.match(name))
    )


def create_bucket(node_settings, bucket_name, location=''):
    return connect_s3compatb3(node_settings=node_settings).create_bucket(Bucket=bucket_name)
    #     CreateBucketConfigurationlocation={'LocationConstraint': location})

def bucket_exists(host, access_key, secret_key, bucket_name):
    """Tests for the existance of a bucket and if the user
    can access it with the given keys
    """
    if not bucket_name:
        return False

    connection = connect_s3compatb3(host, access_key, secret_key)

    exists = True
    try:
        connection.meta.client.head_bucket(Bucket=bucket_name)
    except botocore.exceptions.ClientError as e:
        # If a client error is thrown, then check that it was a 404 error.
        # If it was a 404 error, then the bucket does not exist.
        error_code = e.response['Error']['Code']
        if error_code == '404':
            exists = False
    return exists


def can_list(host, access_key, secret_key):
    """Return whether or not a user can list
    all buckets accessable by this keys
    """
    # Bail out early as boto does not handle getting
    # Called with (None, None)
    if not (host and access_key and secret_key):
        return False

    try:
        connect_s3compatb3(host, access_key, secret_key).buckets.all()
    except exception.S3ResponseError:
        return False
    return True

def get_user_info(host, access_key, secret_key):
    """Returns an S3 Compatible Storage User with .display_name and .id, or None
    """
    if not (access_key and secret_key):
        return None

    try:
        connection = connect_s3compatb3(host, access_key, secret_key)
        buckets = connection.buckets.all()
        [bucket.name for bucket in buckets]
        identity = boto3.client('sts').get_caller_identity()
        return identity
    except ClientError:
        return None
    return None

def get_bucket_location_or_error(host, access_key, secret_key, bucket_name):
    """Returns the location of a bucket or raises AddonError
    """
    try:
        connection = connect_s3compatb3(host, access_key, secret_key)
    except Exception:
        raise InvalidAuthError()

    try:
        # Will raise an exception if bucket_name doesn't exist
        # return connection.get_bucket(bucket_name, validate=False).get_location()
        metadata = connection.meta.client.head_bucket(Bucket=bucket_name)
        return metadata['ResponseMetadata']['HTTPHeaders']['x-amz-bucket-region']
    except exception.S3ResponseError:
        raise InvalidFolderError()
