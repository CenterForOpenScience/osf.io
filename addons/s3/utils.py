import re
import logging
from dataclasses import dataclass

from rest_framework import status as http_status

import boto3
from botocore import exceptions

from framework.exceptions import HTTPError
from addons.base.exceptions import InvalidAuthError, InvalidFolderError
from addons.s3.settings import BUCKET_LOCATIONS

logger = logging.getLogger(__name__)


def connect_s3(access_key=None, secret_key=None, node_settings=None):
    """Helper to build an S3Connection object
    Can be used to change settings on all S3Connections
    See: CallingFormat
    """
    if node_settings is not None:
        if node_settings.external_account is not None:
            access_key, secret_key = node_settings.external_account.oauth_key, node_settings.external_account.oauth_secret
    connection = boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )
    return connection


def get_status_for_error(e: exceptions.ClientError) -> int:
    return e.response['ResponseMetadata']['HTTPStatusCode']


def get_bucket_names(node_settings):
    try:
        response = connect_s3(node_settings=node_settings).list_buckets()
    except exceptions.NoCredentialsError:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    except exceptions.ClientError as e:
        raise HTTPError(get_status_for_error(e))

    return [bucket['Name'] for bucket in response['Buckets']]


def validate_bucket_location(location):
    return location in BUCKET_LOCATIONS


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
    client = connect_s3(node_settings=node_settings)

    # default bucket location won't work with location constraint
    if not location or location == 'us-east-1':
        return client.create_bucket(Bucket=bucket_name)
    else:
        return client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': location,
            }
        )


def bucket_exists(access_key, secret_key, bucket_name):
    """Tests for the existance of a bucket and if the user
    can access it with the given keys
    """
    if not bucket_name:
        return False
    # bucket names are dns-compliant, therefore must be lowercase
    bucket_name = bucket_name.lower()

    try:
        # Will raise an exception if bucket_name doesn't exist
        connect_s3(access_key, secret_key).head_bucket(Bucket=bucket_name)
    except exceptions.ClientError as e:
        if get_status_for_error(e) not in (301, 302):
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
        connect_s3(access_key, secret_key).list_buckets()
    except exceptions.ClientError:
        return False
    return True


@dataclass(slots=True, frozen=True)
class Owner:
    display_name: str
    id: str

    @classmethod
    def from_dict(cls, data):
        return cls(data['DisplayName'], data['ID'])


def get_user_info(access_key: str, secret_key: str) -> Owner | None:
    """Returns an S3 User with .display_name and .id, or None
    """
    if not (access_key and secret_key):
        return None

    try:
        return Owner.from_dict(connect_s3(access_key, secret_key).list_buckets()['Owner'])
    except exceptions.ClientError:
        return None


def get_bucket_location_or_error(access_key, secret_key, bucket_name):
    """Returns the location of a bucket or raises AddonError
    """
    # bucket names are dns-compliant, therefore must be lowercase
    bucket_name = bucket_name.lower()

    try:
        # Will raise an exception if bucket_name doesn't exist
        return connect_s3(access_key, secret_key).get_bucket_location(Bucket=bucket_name)['LocationConstraint']
    except exceptions.NoCredentialsError:
        raise InvalidAuthError()
    except exceptions.ClientError:
        raise InvalidFolderError()


def get_bucket_prefixes(access_key, secret_key, prefix, bucket_name):
    s3 = boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    result = s3.list_objects(Bucket=bucket_name, Prefix=prefix, Delimiter='/')
    folders = []
    for common_prefixes in result.get('CommonPrefixes', []):
        key_name = common_prefixes.get('Prefix')
        if key_name != prefix:
            folders.append(
                {
                    'path': key_name,
                    'id': f'{bucket_name}:/{key_name}',
                    'folder_id': key_name,
                    'kind': 'folder',
                    'bucket_name': bucket_name,
                    'name': key_name.split('/')[-2],
                    'addon': 's3',
                }
            )

    return folders
