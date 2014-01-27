import httplib as http

from framework import request
from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor
from website.project.decorators import must_have_addon
from framework.auth import must_be_logged_in

from website.addons.s3.api import S3Wrapper
from website.addons.s3.api import has_access, does_bucket_exist,remove_user

from website.addons.s3.utils import adjust_cors

from .utils import _s3_create_access_key


@must_be_logged_in
def s3_user_settings(*args, **kwargs):
    user = kwargs['user']
    s3_user = user.get_addon('s3')
    if not s3_user:
        raise HTTPError(http.BAD_REQUEST)

    s3_access_key = request.json.get('access_key', '') or ''
    s3_secret_key = request.json.get('secret_key', '') or ''

    has_auth = (s3_access_key and s3_secret_key)

    changed = (
        s3_access_key != s3_user.access_key or
        s3_secret_key != s3_user.secret_key
    )

    if changed:
        if not has_access(s3_access_key, s3_secret_key):
            error_message = ('Looks like your creditials are incorrect '
                             'Could you have mistyped them?')
            return {'message': error_message}, 400

        s3_user.access_key = s3_access_key
        s3_user.secret_key = s3_secret_key
        s3_user.user_has_auth = has_auth

        s3_user.save()
        return {}


@must_be_contributor
@must_have_addon('s3', 'node')
def s3_settings(*args, **kwargs):

    user = kwargs['user']

    # This should never happen....
    if not user:
        error_message = ''
        return {'message': error_message}, 400

    node = kwargs['node_addon']
    s3_addon = user.get_addon('s3')

    # If authorized, only owner can change settings
    if s3_addon and s3_addon.owner != user:
        raise HTTPError(http.BAD_REQUEST)

    s3_bucket = request.json.get('s3_bucket', '')

    if not s3_bucket or not does_bucket_exist(s3_addon.access_key, s3_addon.secret_key, s3_bucket):
        error_message = ('Looks like this bucket does not exist.'
                         'Could you have mistyped it?')
        return {'message': error_message}, 400

    changed = s3_bucket != node.s3_bucket

    # Delete callback
    if changed:

        # Update node settings
        node.s3_bucket = s3_bucket
        node.save()

        # TODO create access key here figure out way to remove it later?
        if not _s3_create_access_key(s3_addon, node):
                    error_message = ''
                    return {'message': error_message}, 400

        # Last but no least make sure we can upload (must be last) (still no
        # least(but actually))
        adjust_cors(S3Wrapper.from_addon(node))


@must_be_contributor
@must_have_addon('s3', 'node')
def s3_delete_access_key(*args, **kwargs):
    user = kwargs['user']

    s3_node = kwargs['node_addon']
    s3_user = user.get_addon('s3')

    # delete user from amazons data base
    # boto giveth and boto taketh away
    remove_user(s3_user.access_key, s3_user.secret_key,
                s3_node.s3_bucket, s3_node.s3_node_access_key)

    # delete our access and secret key
    s3_node.s3_node_access_key = ''
    s3_node.s3_node_secret_key = ''
    s3_node.node_auth = 0
    s3_node.save()


@must_be_contributor
@must_have_addon('s3', 'user')
def s3_remove_user_settings(*args, **kwargs):
    user = kwargs['user']
    user_settings = user.get_addon('s3')

    user_settings.access_key = ''
    user_settings.secret_key = ''
    user_settings.user_has_auth = False
    user_settings.save()
    return True
