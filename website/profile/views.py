import json
import httplib as http
import bleach

from framework import (
    get_user,
    must_be_logged_in,
    request,
    redirect,
    status
)
from framework.exceptions import HTTPError
from framework.forms.utils import sanitize
from framework.auth import get_current_user, authenticate
from framework.auth.utils import parse_name

from website.models import ApiKey, User
from website.views import _render_nodes
from website import settings
from website.profile import utils


def get_public_projects(uid=None, user=None):
    user = user or User.load(uid)
    return _render_nodes([
        node
        for node in user.node__contributed
        if node.category == 'project'
            and node.is_public
            and not node.is_registration
            and not node.is_deleted
    ])


def get_public_components(uid=None, user=None):
    user = user or User.load(uid)
    return _render_nodes([
        node
        for node in user.node__contributed
        if node.category != 'project'
            and node.is_public
            and not node.is_registration
            and not node.is_deleted
    ])


def _profile_view(uid=None):

    user = get_current_user()
    profile = get_user(id=uid) if uid else user

    if not (uid or user):
        return redirect('/login/?next={0}'.format(request.path))

    if profile:
        profile_user_data = utils.serialize_user(profile, full=True)
        #TODO Fix circular improt
        from website.addons.badges.util import get_sorted_user_badges
        return {
            'profile': profile_user_data,
            'assertions': get_sorted_user_badges(profile),
            'badges': _get_user_created_badges(profile),
            'user': {
                'is_profile': user == profile,
                'can_edit': None,  # necessary for rendering nodes
                'permissions': [], # necessary for rendering nodes
            },
        }

    raise HTTPError(http.NOT_FOUND)


def _get_user_created_badges(user):
    addon = user.get_addon('badges')
    if addon:
        return [badge for badge in addon.badge__creator if not badge.is_system_badge]
    return []


def profile_view():
    return _profile_view()


def profile_view_id(uid):
    return _profile_view(uid)


@must_be_logged_in
def edit_profile(**kwargs):

    user = kwargs['auth'].user

    form = request.form

    response_data = {'response': 'success'}
    if form.get('name') == 'fullname' and form.get('value', '').strip():
        user.fullname = sanitize(form['value'])
        user.save()
        response_data['name'] = user.fullname
    return response_data


def get_profile_summary(user_id, formatter='long'):

    user = User.load(user_id)
    return user.get_summary(formatter)


profile_schema = {
    'pages': [
        {
            'id': 'null',
            'title': 'Names',
            'contents': [
                {
                    'id': 'fullname',
                    'type': 'textfield',
                    'label': 'Full/display name',
                    'required': True,
                    'helpText': 'The field above is your full name and the name that will be '
                                'displayed in your profile. You can use the "Guess fields" button '
                                'or edit the fields below in order to accurately generate '
                                'citations.',
                },
                {
                    'id': 'impute',
                    'type': 'htmlfield',
                    'label': '',
                    'content': '<button id="profile-impute" class="btn btn-default">Guess fields</button>',
                },
                {
                    'id': 'given_name',
                    'type': 'textfield',
                    'label': 'Given name',
                    'helpText': 'First name; e.g., Stephen',
                },
                {
                    'id': 'middle_names',
                    'type': 'textfield',
                    'label': 'Middle name(s)',
                    'helpText': 'Middle names; e.g., Jay',
                },
                {
                    'id': 'family_name',
                    'type': 'textfield',
                    'label': 'Family name',
                    'required': True,
                    'helpText': 'Surname; e.g., Gould',
                },
                {
                    'id': 'suffix',
                    'type': 'textfield',
                    'label': 'Suffix',
                    'helpText': 'E.g., Sr., Jr., III',
                },
            ]
        }
    ]
}


# TODO: Similar to node_setting; refactor
@must_be_logged_in
def profile_settings(**kwargs):

    user = kwargs['auth'].user

    rv = {
        'user_id': user._primary_key,
        'user_api_url': user.api_url,
        'names': json.dumps({
            'fullname': user.fullname,
            'given_name': user.given_name,
            'middle_names': user.middle_names,
            'family_name': user.family_name,
            'suffix': user.suffix,
        }),
        'schema': json.dumps(profile_schema),
    }

    addons_enabled = []
    addon_enabled_settings = []

    for addon in user.get_addons():

        addons_enabled.append(addon.config.short_name)

        if 'user' in addon.config.configs:
            addon_enabled_settings.append(addon.config.short_name)

    rv['addon_categories'] = settings.ADDON_CATEGORIES
    rv['addons_available'] = [
        addon
        for addon in settings.ADDONS_AVAILABLE
        if 'user' in addon.owners
        and not addon.short_name in settings.SYSTEM_ADDED_ADDONS['user']
    ]
    rv['addons_enabled'] = addons_enabled
    rv['addon_enabled_settings'] = addon_enabled_settings

    return rv


@must_be_logged_in
def profile_addons(**kwargs):
    user = kwargs['auth'].user
    return {
        'user_id': user._primary_key,
    }


@must_be_logged_in
def user_choose_addons(**kwargs):
    auth = kwargs['auth']
    auth.user.config_addons(request.json, auth)


@must_be_logged_in
def get_keys(**kwargs):
    user = kwargs['auth'].user
    return {
        'keys': [
            {
                'key': key._id,
                'label': key.label,
            }
            for key in user.api_keys
        ]
    }


@must_be_logged_in
def create_user_key(**kwargs):

    # Generate key
    api_key = ApiKey(label=request.form['label'])
    api_key.save()

    # Append to user
    user = kwargs['auth'].user
    user.api_keys.append(api_key)
    user.save()

    # Return response
    return {
        'response': 'success',
    }


@must_be_logged_in
def revoke_user_key(**kwargs):

    # Load key
    api_key = ApiKey.load(request.form['key'])

    # Remove from user
    user = kwargs['auth'].user
    user.api_keys.remove(api_key)
    user.save()

    # Return response
    return {'response': 'success'}


@must_be_logged_in
def user_key_history(**kwargs):

    api_key = ApiKey.load(kwargs['kid'])
    return {
        'key': api_key._id,
        'label': api_key.label,
        'route': '/settings',
        'logs': [
            {
                'lid': log._id,
                'nid': log.node__logged[0]._id,
                'route': log.node__logged[0].url,
            }
            for log in api_key.nodelog__created
        ]
    }


@must_be_logged_in
def parse_names(**kwargs):
    name = request.json.get('fullname', '')
    return parse_name(name)


NAME_FIELDS = [
    'fullname', 'given_name', 'middle_names', 'family_name', 'suffix'
]
def scrub_html(value):
    return bleach.clean(value, strip=True, tags=[], attributes=[], styles=[])


@must_be_logged_in
def post_names(**kwargs):
    user = kwargs['auth'].user
    for field in NAME_FIELDS:
        setattr(user, field, scrub_html(request.json[field]))
    user.save()
