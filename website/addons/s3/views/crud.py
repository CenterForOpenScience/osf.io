import httplib

from flask import request
from boto import exception

from website.addons.s3 import utils
from website.project.decorators import must_have_addon
from website.project.decorators import must_have_permission
#from website.addons.s3.api import create_folder
from website.addons.s3 import utils
from website.project.decorators import must_be_contributor_or_public


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
@must_have_permission('write')

def create_bucket(node_addon, **kwargs):
    user = kwargs['auth'].user
    user_settings = user.get_addon('s3')

    bucket_name = request.json.get('folder_name', '')

    if not utils.validate_bucket_name(bucket_name):
        return {
            'message': 'That bucket name is not valid.',
            'title': 'Invalid bucket name',
        }, httplib.NOT_ACCEPTABLE

    try:
        utils.create_bucket(node_addon.user_settings, bucket_name)
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

    return {
        'buckets': utils.get_bucket_names(node_addon.user_settings)
    }
