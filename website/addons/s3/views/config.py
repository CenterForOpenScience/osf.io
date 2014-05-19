import httplib as http

from boto.exception import BotoServerError

from framework import request
from framework.exceptions import HTTPError
from framework.status import push_status_message
from framework.auth.decorators import must_be_logged_in

from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

from website.addons.s3.api import S3Wrapper, has_access, does_bucket_exist
from website.addons.s3.utils import adjust_cors, create_osf_user


def add_s3_auth(access_key, secret_key, user_settings):

    if not has_access(access_key, secret_key):
        return False

    user_name, access_key = create_osf_user(
        access_key, secret_key, user_settings.owner.family_name
    )

    user_settings.s3_osf_user = user_name
    user_settings.access_key = access_key['access_key_id']
    user_settings.secret_key = access_key['secret_access_key']

    user_settings.save()
    return True


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

    try:
        if not add_s3_auth(s3_access_key, s3_secret_key, user_settings):
            return {'message': 'Incorrect credentials'}, http.BAD_REQUEST
    except BotoServerError:
        #Note: Can't send back mark up :[
        return {
            'message': 'Could not access IAM. Please allow these keys permission.'
        }, http.BAD_REQUEST
    return {}


@must_have_permission('write')
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

    if not add_s3_auth(s3_access_key, s3_secret_key, user_settings):
        return {'message': 'Incorrect credentials'}, http.BAD_REQUEST

    node_settings.user_settings = user_settings
    node_settings.save()

    return {}


@must_have_permission('write')
@must_have_addon('s3', 'node')
@must_not_be_registration
def s3_node_settings(**kwargs):

    auth = kwargs['auth']
    user = auth.user
    node_settings = kwargs['node_addon']
    node = node_settings.owner

    user_settings = user.get_addon('s3')

    # Fail if no user settings
    if user_settings is None:
        raise HTTPError(http.BAD_REQUEST)

    # Fail if user settings not authorized
    if None in [user_settings.access_key, user_settings.secret_key]:
        raise HTTPError(http.BAD_REQUEST)

    # If authorized, only owner can change settings
    if node_settings.user_settings and node_settings.user_settings.owner != user:
        raise HTTPError(http.BAD_REQUEST)

    # Claiming the node settings
    if not node_settings.user_settings:
        node_settings.user_settings = user_settings

    bucket = request.json.get('s3_bucket', '')

    if not bucket or not does_bucket_exist(user_settings.access_key, user_settings.secret_key, bucket):
        error_message = ('We are having trouble connecting to that bucket. '
                         'Try a different one.')
        return {'message': error_message}, http.BAD_REQUEST

    if bucket != node_settings.bucket:

        # Update node settings
        node_settings.bucket = bucket
        node_settings.save()

        node.add_log(
            action='s3_bucket_linked',
            params={
                'project': node.parent_id,
                'node': node._id,
                'bucket': node_settings.bucket,
            },
            auth=auth,
        )

        adjust_cors(S3Wrapper.from_addon(node_settings))


@must_have_permission('write')
@must_have_addon('s3', 'node')
def s3_remove_node_settings(**kwargs):

    auth = kwargs['auth']
    node_settings = kwargs['node_addon']
    node = node_settings.owner

    bucket = node_settings.bucket
    node_settings.user_settings = None
    node_settings.bucket = None
    node_settings.save()

    if bucket:
        node.add_log(
            action='s3_bucket_unlinked',
            params={
                'project': node.parent_id,
                'node': node._id,
                'bucket': bucket,
            },
            auth=auth,
        )


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
