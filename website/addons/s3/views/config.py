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
@must_have_addon('s3', 'user')
def s3_user_settings(*args, **kwargs):
    user = kwargs['user']
    s3_user = user.get_addon('s3')
    if not s3_user:
        raise HTTPError(http.BAD_REQUEST)

    s3_access_key = request.json.get('access_key', '') or ''
    s3_secret_key = request.json.get('secret_key', '') or ''


    changed = (
        s3_access_key != s3_user.access_key or
        s3_secret_key != s3_user.secret_key
    )

    if changed or not s3_user.has_auth:
        if not has_access(s3_access_key, s3_secret_key):
            error_message = ('Looks like your creditials are incorrect. '
                             'Could you have mistyped them?')
            return {'message': error_message}, 400

        s3_user.access_key = s3_access_key
        s3_user.secret_key = s3_secret_key

        s3_user.save()
        return {}


@must_be_contributor
@must_have_addon('s3', 'node')
def s3_settings(*args, **kwargs):

    user = kwargs['user']

    # This should never happen....
    if not user:
        return 400

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

    changed = bucket != node.bucket

    # Delete callback
    if changed or not node.node_auth:

        # Update node settings
        node.bucket = bucket
        node.save()

        # TODO create access key here figure out way to remove it later?
        if not _s3_create_access_key(s3_addon, node, str(kwargs['pid'])):
                    error_message = ''
                    return {'message': error_message}, 400

        # Last but no least make sure we can upload (must be last) (still no
        # least(but actually))
        #This fails for some reason....
        #I dont like this solutions TODO find a better way
        #Seems like there is some lag from creating the key hmmm
        adjust_cors(S3Wrapper.from_user(s3_addon, bucket))

#TODO Rename me
@must_be_contributor
@must_have_addon('s3', 'node')
def s3_delete_access_key(*args, **kwargs):
    user = kwargs['user']

    s3_node = kwargs['node_addon']
    s3_user = user.get_addon('s3')

    # delete user from amazons data base
    # boto giveth and boto taketh away
    remove_user(s3_user.access_key, s3_user.secret_key,
                s3_node.bucket, s3_node.node_access_key, str(kwargs['pid']))

    # delete our access and secret key
    s3_node.node_access_key = ''
    s3_node.node_secret_key = ''
    s3_node.bucket = ''
    s3_node.save()
    return True


@must_be_logged_in
@must_have_addon('s3', 'user')
def s3_remove_user_settings(*args, **kwargs):
    user = kwargs['user']
    user_settings = user.get_addon('s3')

    user_settings.access_key = ''
    user_settings.secret_key = ''
    user_settings.save()
    return True


@must_be_contributor
@must_have_addon('s3', 'node')
def force_removal(*args, **kwargs):
    s3_node = kwargs['node_addon']

    # delete our access and secret key
    s3_node.node_access_key = ''
    s3_node.node_secret_key = ''
    s3_node.bucket = ''
    s3_node.save()
    return True
