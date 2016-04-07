import httplib
import urllib

from flask import request

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from website.addons.sharelatex import utils
from website.project.decorators import must_have_addon
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration


@must_be_logged_in
def sharelatex_post_user_settings(auth, **kwargs):
    user_addon = auth.user.get_or_add_addon('sharelatex')
    try:
        sharelatex_url = request.json['sharelatex_url'].strip('/')
        auth_token = request.json['auth_token'].strip()
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    if not (sharelatex_url and auth_token):
        return {
            'message': ('All the fields above are required.')
        }, httplib.BAD_REQUEST

    if not utils.can_list(sharelatex_url, auth_token):
        return {
            'message': ('Unable to list projects.\n'
                'Listing projects is required permission that can be changed via IAM')
        }, httplib.BAD_REQUEST

    try:
        urllib.urlopen(sharelatex_url)
    except ValueError:
        return {
            'message': ('Invalid URL.\n'
                'Please inform a valid URL starting with http:// or https://')
        }, httplib.BAD_REQUEST

    user_addon.sharelatex_url = sharelatex_url
    user_addon.auth_token = auth_token

    user_addon.save()


@must_have_permission('write')
@must_have_addon('sharelatex', 'node')
def sharelatex_authorize_node(auth, node_addon, **kwargs):
    try:
        sharelatex_url = request.json['sharelatex_url']
        auth_token = request.json['auth_token']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    if not (sharelatex_url and auth_token):
        return {
            'message': 'All the fields above are required.'
        }, httplib.BAD_REQUEST

    if not utils.can_list(sharelatex_url, auth_token):
        return {
            'message': ('Unable to list projects.\n'
                'Listing projects is required permission that can be changed via IAM')
        }, httplib.BAD_REQUEST

    user_addon = auth.user.get_or_add_addon('sharelatex')

    user_addon.sharelatex_url = sharelatex_url
    user_addon.auth_token = auth_token

    user_addon.save()

    node_addon.authorize(user_addon, save=True)

    return node_addon.to_json(auth.user)


@must_be_logged_in
@must_have_permission('write')
@must_have_addon('sharelatex', 'node')
@must_have_addon('sharelatex', 'user')
def sharelatex_node_import_auth(auth, node_addon, user_addon, **kwargs):
    node_addon.authorize(user_addon, save=True)
    return node_addon.to_json(auth.user)


@must_have_permission('write')
@must_have_addon('sharelatex', 'user')
@must_have_addon('sharelatex', 'node')
@must_not_be_registration
def sharelatex_post_node_settings(node, auth, user_addon, node_addon, **kwargs):
    # Fail if user settings not authorized
    if not user_addon.has_auth:
        raise HTTPError(httplib.BAD_REQUEST)

    # If authorized, only owner can change settings
    if node_addon.has_auth and node_addon.user_settings.owner != auth.user:
        raise HTTPError(httplib.BAD_REQUEST)

    # Claiming the node settings
    if not node_addon.user_settings:
        node_addon.user_settings = user_addon

    project = request.json.get('sharelatex_project', '')

    if not utils.project_exists(user_addon.sharelatex_url, user_addon.auth_token, project):
        error_message = ('We are having trouble connecting to that project. '
                         'Try a different one.')
        return {'message': error_message}, httplib.BAD_REQUEST

    if project != node_addon.project:

        # Update node settings
        node_addon.project = project
        node_addon.save()

        node.add_log(
            action='sharelatex_project_linked',
            params={
                'node': node._id,
                'project': node.parent_id,
                'projectsharelatex': node_addon.project,
            },
            auth=auth,
        )

    return node_addon.to_json(auth.user)


@must_be_logged_in
@must_have_addon('sharelatex', 'node')
@must_have_permission('write')
@must_not_be_registration
def sharelatex_get_node_settings(auth, node_addon, **kwargs):
    result = node_addon.to_json(auth.user)
    result['urls'] = utils.serialize_urls(node_addon, auth.user)

    return {'result': result}


@must_be_logged_in
@must_have_addon('sharelatex', 'node')
@must_have_addon('sharelatex', 'user')
@must_have_permission('write')
@must_not_be_registration
def sharelatex_get_project_list(auth, node_addon, user_addon, **kwargs):
    data = utils.get_project_list(user_addon)
    result = []
    for p in data:
        result.append({'id': p['_id'], 'name': p['name']})
    return result


@must_have_permission('write')
@must_have_addon('sharelatex', 'node')
@must_not_be_registration
def sharelatex_delete_node_settings(auth, node_addon, **kwargs):
    node_addon.deauthorize(auth=auth, save=True)
    return node_addon.to_json(auth.user)


@must_be_logged_in
@must_have_addon('sharelatex', 'user')
def sharelatex_delete_user_settings(user_addon, auth, **kwargs):
    user_addon.revoke_auth(auth=auth, save=True)
    user_addon.delete()
    user_addon.save()
