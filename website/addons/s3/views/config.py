import httplib as http

from framework import request
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from website.project.decorators import must_be_contributor
from website.project.decorators import must_have_addon

from website.addons.s3.api import S3Wrapper
from website.addons.s3.api import has_access, does_bucket_exist

from website.addons.s3.utils import adjust_cors, create_osf_user, remove_osf_user


def add_s3_auth(access_key, secret_key, user_settings):

    if not has_access(access_key, secret_key):
        return {'message': 'Incorrect credentials'}, 400

    keys = create_osf_user(access_key, secret_key, user_settings.owner.family_name)

    user_settings.access_key = keys['access_key_id']
    user_settings.secret_key = keys['secret_access_key']

    user_settings.save()


@must_be_logged_in
@must_have_addon('s3', 'user')
def s3_authorize_user(**kwargs):

    user = kwargs['auth'].user
    user_settings = user.get_addon('s3')
    if not user_settings:
        raise HTTPError(http.BAD_REQUEST)

    s3_access_key = request.json.get('access_key')
    s3_secret_key = request.json.get('secret_key')
    if not s3_access_key or not s3_secret_key:
        raise HTTPError(http.BAD_REQUEST)

    add_s3_auth(s3_access_key, s3_secret_key, user_settings)

    return {}


@must_be_contributor
@must_have_addon('s3', 'node')
def s3_authorize_node(**kwargs):

    user = kwargs['auth'].user
    node_settings = kwargs['node_addon']

    s3_access_key = request.json.get('access_key')
    s3_secret_key = request.json.get('secret_key')
    if s3_access_key is None or s3_secret_key is None:
        raise HTTPError(http.BAD_REQUEST)

    user_settings = user.get_addon('s3')
    if user_settings is None:
        user.add_addon('s3')
        user_settings = user.get_addon('s3')

    add_s3_auth(s3_access_key, s3_secret_key, user_settings)

    node_settings.user_settings = user_settings
    node_settings.save()

    return {}


@must_be_contributor
@must_have_addon('s3', 'node')
def s3_node_settings(**kwargs):

    user = kwargs['auth'].user
    node = kwargs['node_addon']
    s3_addon = user.get_addon('s3')

    # If authorized, only owner can change settings
    if s3_addon and s3_addon.owner != user:
        raise HTTPError(http.BAD_REQUEST)

    bucket = request.json.get('s3_bucket', '')

    if not bucket or not does_bucket_exist(s3_addon.access_key, s3_addon.secret_key, bucket):
        error_message = ('We are having trouble connecting to that bucket. '
                         'Try a different one.')
        return {'message': error_message}, 400

    if bucket != node.bucket:

        # Update node settings
        node.bucket = bucket
        node.save()

        adjust_cors(S3Wrapper.from_addon(node))


@must_be_logged_in
@must_have_addon('s3', 'user')
def s3_remove_user_settings(**kwargs):
    user = kwargs['auth'].user
    user_settings = user.get_addon('s3')

    remove_osf_user(user_settings)

    user_settings.access_key = ''
    user_settings.secret_key = ''
    user_settings.save()

    return {}
