import httplib as http
from framework import (
    abort,
    get_current_user,
    get_user,
    must_be_logged_in,
    request,
)
from framework.forms.utils import sanitize

from website.models import ApiKey
from framework.analytics import get_total_activity_count


def _node_info(node):
    return {
        'api_url' : node.api_url(),
    }


def get_public_projects(user):
    return [
        _node_info(node)
        for node in user.node__contributed
        if node.category == 'project'
        and node.is_public
        and not node.is_deleted
    ]


def get_public_components(user):
    return [
        _node_info(node)
        for node in user.node__contributed
        if node.category != 'project'
        and node.is_public
        and not node.is_deleted
    ]


def profile_view(uid=None):
    user = get_current_user()
    profile = get_user(id=uid or user)

    if not (uid or user):
        abort(http.UNAUTHORIZED)

    if profile:
        projects = [
            node
            for node in profile.node__contributed
            if node.category == 'project'
            and not node.is_registration
            and not node.is_deleted
        ]
        public_projects = get_public_projects(user)
        public_components = get_public_components(user)
        return {
            'user_id': profile._id,
            'user_is_profile' : user == profile,
            'activity_points' : get_total_activity_count(profile._primary_key),
            'number_projects' : len(projects),
            'number_public_projects' : len(public_projects),
            'fullname': profile.fullname,
            'date_registered': profile.date_registered.strftime("%Y-%m-%d"),
            'public_projects' : public_projects,
            'public_components' : public_components,
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
        'user_id' : user._primary_key,
    }


@must_be_logged_in
def profile_addons(*args, **kwargs):
    user = kwargs['user']
    return {
        'user_id' : user._primary_key,
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