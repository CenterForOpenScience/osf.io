from framework import (
    abort,
    get,
    get_current_user,
    get_user,
    jsonify,
    must_be_logged_in,
    post,
    redirect,
    render,
    request,
)
from framework.forms.utils import sanitize

from website.models import User, ApiKey
from framework.analytics import get_total_activity_count

def _node_info(node):
    if node.category == 'project':
        route = '/project/{}'.format(
            node._id
        )
        parent, parent_id = None, None
    else:
        parent = node.node__parent[0]
        parent_id = parent._id
        route = '/project/{}/node/{}'.format(
            parent._id,
            node._id,
        )
    return {
        'node_id' : node._id,
        'parent_id' : parent_id,
        'route' : route,
    }


def get_public_projects(uid):
    user = User.load(uid)
    return [
        _node_info(node)
        for node in user.node__contributed
        if node.category == 'project'
        and node.is_public
        and not node.is_deleted
    ]

def get_public_components(*args, **kwargs):
    user = User.load(kwargs['uid'])
    return [
        _node_info(node)
        for node in user.node__contributed
        if node.category != 'project'
        and node.is_public
        and not node.is_deleted
    ]

@must_be_logged_in
def profile_view(*args, **kwargs):
    user = kwargs['user']
    projects = [
        node
        for node in user.node__contributed
        if node.category == 'project'
        and not node.is_registration
        and not node.is_deleted
    ]
    public_projects = [
        node
        for node in projects
        if node.is_public
    ]
    return {
        'profile' : user,
        'profile_id' : user._id,
        'user' : user,
        'user_id': user._id,
        'activity_points' : get_total_activity_count(user._primary_key),
        'number_projects' : len(projects),
        'number_public_projects' : len(public_projects),
    }


def profile_view_id(uid):
    profile = get_user(id=uid)
    user = get_current_user()
    if profile:
        projects = [
            node
            for node in profile.node__contributed
            if node.category == 'project'
            and not node.is_registration
            and not node.is_deleted
        ]
        public_projects = [
            node
            for node in projects
            if node.is_public
        ]
        return {
            'profile' : profile,
            'profile_id' : profile._id,
            'user' : user,
            'user_id': user._id,
            'activity_points' : get_total_activity_count(profile._primary_key),
            'number_projects' : len(projects),
            'number_public_projects' : len(public_projects),
        }
    return abort(404)


@must_be_logged_in
def edit_profile(*args, **kwargs):
    user = kwargs['user']
    
    form = request.form

    if form.get('name') == 'fullname' and form.get('value', '').strip():
        user.fullname = sanitize(form['value'])
        user.save()

    return {'response' : 'success'}


@must_be_logged_in
def profile_settings(*args, **kwargs):
    user = kwargs['user']
    return {
        'user' : user,
    }

@must_be_logged_in
def get_keys(*args, **kwargs):
    user = kwargs['user']
    return [
        {
            'key' : key._id,
            'label' : key.label,
        }
        for key in user.api_keys
    ]

@must_be_logged_in
def create_user_key(*args, **kwargs):

    # Generate key
    api_key = ApiKey(label=request.form['label'])
    api_key.save()

    # Append to user
    user = get_current_user()
    user.api_keys.append(api_key)
    user.save()

    # Return response
    return {
        'response' : 'success',
    }

@must_be_logged_in
def revoke_user_key(*args, **kwargs):

    # Load key
    api_key = ApiKey.load(request.form['key'])

    # Remove from user
    user = get_current_user()
    user.api_keys.remove(api_key)
    user.save()

    # Return response
    return {'response' : 'success'}

@must_be_logged_in
def user_key_history(*args, **kwargs):

    api_key = ApiKey.load(kwargs['kid'])
    return {
        'key' : api_key._id,
        'label' : api_key.label,
        'user' : kwargs['user'],
        'route' : '/settings',
        'logs' : [
            {
                'lid' : log._id,
                'nid' : log.node__logged[0]._id,
                'route' : log.node__logged[0].url(),
            }
            for log in api_key.nodelog__created
        ]
    }