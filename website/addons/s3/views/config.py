import httplib as http

from framework import request
from framework.exceptions import HTTPError
from framework.status import push_status_message
from framework.auth.decorators import must_be_logged_in

from website.project.decorators import must_be_contributor
from website.project.decorators import must_have_addon

from website.addons.s3.api import S3Wrapper
from website.addons.s3.api import has_access, does_bucket_exist

from website.addons.s3.utils import adjust_cors, create_osf_user


def add_s3_auth(access_key, secret_key, user_settings):

    if not has_access(access_key, secret_key):
        return {'message': 'Incorrect credentials'}, http.BAD_REQUEST

    user_name, access_key = create_osf_user(
        access_key, secret_key, user_settings.owner.family_name
    )

    user_settings.s3_osf_user = user_name
    user_settings.access_key = access_key['access_key_id']
    user_settings.secret_key = access_key['secret_access_key']

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
    if not s3_access_key or not s3_secret_key:
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
    node_settings = kwargs['node_addon']
    user_settings = user.get_addon('s3')

    # Claiming the node settings
    if not node_settings.user_settings:
        node_settings.user_settings = user_settings
    # If authorized, only owner can change settings
    if user_settings and user_settings.owner != user:
        raise HTTPError(http.BAD_REQUEST)

    bucket = request.json.get('s3_bucket', '')

    if not bucket or not does_bucket_exist(user_settings.access_key, user_settings.secret_key, bucket):
        error_message = ('We are having trouble connecting to that bucket. '
                         'Try a different one.')
        return {'message': error_message}, http.BAD_REQUEST

    if bucket != node_settings.bucket:

        # Update node settings
        node_settings.bucket = bucket
        node_settings.save()

        adjust_cors(S3Wrapper.from_addon(node_settings))


@must_be_contributor
@must_have_addon('s3', 'node')
def s3_remove_node_settings(**kwargs):
    node_settings = kwargs['node_addon']
    node_settings.user_settings = None
    node_settings.bucket = None
    node_settings.save()


@must_be_logged_in
@must_have_addon('s3', 'user')
def s3_remove_user_settings(**kwargs):

    user_settings = kwargs['user_addon']

    success = user_settings.revoke_auth()

    if not success:
        push_status_message(
            'Your Amazon credentials were removed from the OSF, but we were '
            'unable to revoke your OSF information from Amazon. Your Amazon '
            'credentials may no longer be valid.'
        )
        return {'message': 'reload'}, http.BAD_REQUEST

    return {}
