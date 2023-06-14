import re
from rest_framework import status as http_status

import boto3
from botocore.exceptions import NoCredentialsError, ClientError

from framework.exceptions import HTTPError
from addons.base.exceptions import InvalidAuthError, InvalidFolderError
from addons.s3.settings import BUCKET_LOCATIONS


def connect_s3(access_key=None, secret_key=None, node_settings=None):
    """Helper to build an S3 client object
    Can be used to change settings on all S3 clients
    """
    if node_settings is not None:
        if node_settings.external_account is not None:
            access_key, secret_key = node_settings.external_account.oauth_key, node_settings.external_account.oauth_secret
    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )
    client = session.client('s3')
    return client


def get_bucket_names(node_settings):
    try:
        buckets = connect_s3(node_settings=node_settings).list_buckets()['Buckets']
    except NoCredentialsError:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    except ClientError as e:
        raise HTTPError(e.response['ResponseMetadata']['HTTPStatusCode'])

    return [bucket['Name'] for bucket in buckets]


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
    create_bucket_config = {'Bucket': bucket_name}
    if location:
        create_bucket_config['CreateBucketConfiguration'] = {'LocationConstraint': location}
    client.create_bucket(**create_bucket_config)


def bucket_exists(access_key, secret_key, bucket_name):
    """Tests for the existence of a bucket and if the user
    can access it with the given keys
    """
    if not bucket_name:
        return False

    client = connect_s3(access_key, secret_key)

    if bucket_name != bucket_name.lower():
        # Must use ordinary calling format for mIxEdCaSe bucket names
        # otherwise use the default as it handles buckets outside of the US
        client.meta.client.meta.events.unregister('before-sign.s3', boto3._inject_normally_invalid_bucket_name_path)

    try:
        # Will raise an exception if bucket_name doesn't exist
        client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        if e.response['ResponseMetadata']['HTTPStatusCode'] not in (301, 302):
            return False
    return True


def can_list(access_key, secret_key):
    """Return whether or not a user can list
    all buckets accessible by these keys
    """
    # Bail out early as boto3 does not handle getting
    # called with (None, None)
    if not (access_key and secret_key):
        return False

    try:
        connect_s3(access_key, secret_key).list_buckets()
    except NoCredentialsError:
        return False
    return True


def get_user_info(access_key, secret_key):
    """Returns an S3 User with .display_name and .id, or None
    """
    if not (access_key and secret_key):
        return None

    try:
        response = connect_s3(access_key, secret_key).list_buckets()
        owner = response['Owner']
        return {
            'display_name': owner['DisplayName'],
            'id': owner['ID']
        }
    except NoCredentialsError:
        return None


def get_bucket_location_or_error(access_key, secret_key, bucket_name):
    """Returns the location of a bucket or raises AddonError
    """
    try:
        client = connect_s3(access_key, secret_key)
    except Exception:
        raise InvalidAuthError()

    if bucket_name != bucket_name.lower() or '.' in bucket_name:
        # Must use ordinary calling format for mIxEdCaSe bucket names
        # otherwise use the default as it handles buckets outside of the US
        client.meta.client.meta.events.unregister('before-sign.s3', boto3._inject_normally_invalid_bucket_name_path)

    try:
        response = client.get_bucket_location(Bucket=bucket_name)
        return response['LocationConstraint']
    except ClientError:
        raise InvalidFolderError()
