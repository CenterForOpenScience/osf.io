import httplib
import json

from flask import request
from boto import exception


from website.addons.s3 import utils
from website.addons.s3.settings import DEFAULT_BUCKET_LOCATION
from website.addons.s3.settings import BUCKET_ENCRYPTION_DEFAULT_ON as ENCRYPT
from website.project.decorators import must_have_addon
from website.project.decorators import must_have_permission
from website.project.decorators import must_be_contributor_or_public


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
@must_have_permission('write')
def create_bucket(auth, node_addon, **kwargs):
    bucket_name = request.json.get('bucket_name', '')
    bucket_location = request.json.get('bucket_location', DEFAULT_BUCKET_LOCATION['value'])
    encrypt_bucket = request.json.get('encrypt_bucket', ENCRYPT)

    if not utils.validate_bucket_name(bucket_name):
        return {
            'message': 'That bucket name is not valid.',
            'title': 'Invalid bucket name',
        }, httplib.NOT_ACCEPTABLE

    # Get location and verify it is valid
    if not utils.valid_bucket_location(bucket_location):
        return {
            'message': 'That bucket location is not valid.',
            'title': 'Invalid bucket location',
        }, httplib.NOT_ACCEPTABLE

    try:
        bucket = utils.create_bucket(node_addon.user_settings, bucket_name, bucket_location)
    except exception.S3ResponseError as e:
        return {
            'message': e.message,
            'title': 'Problem connecting to S3',
        }, httplib.NOT_ACCEPTABLE
    except exception.S3CreateError as e:
        return {
            'message': e.message,
            'title': "Problem creating bucket '{0}'".format(bucket_name),
        }, httplib.NOT_ACCEPTABLE
    except exception.BotoClientError as e:  # Base class catchall
        return {
            'message': e.message,
            'title': 'Error connecting to S3',
        }, httplib.NOT_ACCEPTABLE

    if encrypt_bucket:
        bucket.set_policy(
            policy=json.dumps(
                {
                    "Id": "PutObjectPolicy",
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "DenyUnencryptedObjectUploads",
                            "Action": [
                                "s3:PutObject"
                            ],
                            "Effect": "Deny",
                            "Resource": "arn:aws:s3:::{0}/*".format(bucket.name),
                            "Condition": {
                                "StringNotEquals": {
                                    "s3:x-amz-server-side-encryption": "AES256"
                                }
                            },
                            "Principal": "*"
                        }
                    ]
                }
            )
        )

    return {
        'buckets': utils.get_bucket_names(node_addon.user_settings)
    }
