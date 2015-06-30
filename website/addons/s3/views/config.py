import httplib

from flask import request

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from website.addons.s3 import utils
from website.project.decorators import must_have_addon
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration


@must_be_logged_in
@must_have_addon('s3', 'user')
def s3_post_user_settings(user_addon, **kwargs):
    try:
        access_key = request.json['access_key']
        secret_key = request.json['secret_key']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    if not utils.can_list(access_key, secret_key):
        return {
            'message': ('Unable to list buckets.\n'
                'Listing buckets is required permission that can be changed via IAM')
        }, httplib.BAD_REQUEST

    user_addon.access_key = access_key
    user_addon.secret_key = secret_key

    user_addon.save()


@must_have_permission('write')
@must_have_addon('s3', 'node')
def s3_authorize_node(auth, node_addon, **kwargs):
    try:
        access_key = request.json['access_key']
        secret_key = request.json['secret_key']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    if not utils.can_list(access_key, secret_key):
        return {
            'message': ('Unable to list buckets.\n'
                'Listing buckets is required permission that can be changed via IAM')
        }, httplib.BAD_REQUEST

    user_addon = auth.user.get_or_add_addon('s3')

    user_addon.access_key = access_key
    user_addon.secret_key = secret_key

    user_addon.save()

    node_addon.authorize(user_addon, save=True)

    return node_addon.to_json(auth.user)


@must_be_logged_in
@must_have_permission('write')
@must_have_addon('s3', 'node')
@must_have_addon('s3', 'user')
def s3_node_import_auth(auth, node_addon, user_addon, **kwargs):
    node_addon.authorize(user_addon, save=True)
    return node_addon.to_json(auth.user)


@must_have_permission('write')
@must_have_addon('s3', 'user')
@must_have_addon('s3', 'node')
@must_not_be_registration
def s3_post_node_settings(node, auth, user_addon, node_addon, **kwargs):
    # Fail if user settings not authorized
    if not user_addon.has_auth:
        raise HTTPError(httplib.BAD_REQUEST)

    # If authorized, only owner can change settings
    if node_addon.has_auth and node_addon.user_settings.owner != auth.user:
        raise HTTPError(httplib.BAD_REQUEST)

    # Claiming the node settings
    if not node_addon.user_settings:
        node_addon.user_settings = user_addon

    bucket = request.json.get('folder', '')

    if not utils.bucket_exists(user_addon.access_key, user_addon.secret_key, bucket):
        error_message = ('We are having trouble connecting to that bucket. '
                         'Try a different one.')
        return {'message': error_message}, httplib.BAD_REQUEST

    if bucket != node_addon.bucket:

        # Update node settings
        node_addon.bucket = bucket
        node_addon.save()

        node.add_log(
            action='s3_bucket_linked',
            params={
                'node': node._id,
                'project': node.parent_id,
                'bucket': node_addon.bucket,
            },
            auth=auth,
        )

    return node_addon.to_json(auth.user)


@must_be_logged_in
@must_have_addon('s3', 'node')
@must_have_permission('write')
@must_not_be_registration
def s3_get_node_settings(auth, node_addon, **kwargs):
    result = node_addon.to_json(auth.user)
    result['urls'] = utils.serialize_urls(node_addon, auth.user)

    return {'result': result}


@must_be_logged_in
@must_have_addon('s3', 'node')
@must_have_addon('s3', 'user')
@must_have_permission('write')
@must_not_be_registration
def s3_get_bucket_list(auth, node_addon, user_addon, **kwargs):
    return {
        'buckets': utils.get_bucket_names(user_addon)
    }


@must_have_permission('write')
@must_have_addon('s3', 'node')
@must_not_be_registration
def s3_delete_node_settings(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth, save=True)
    return node_addon.to_json(auth.user)


@must_be_logged_in
@must_have_addon('s3', 'user')
def s3_delete_user_settings(user_addon, **kwargs):
    user_addon.revoke_auth(save=True)
