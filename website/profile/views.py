import json
import httplib as http

from framework import (
    get_current_user,
    get_user,
    must_be_logged_in,
    request,
    redirect,
)
from framework.auth import must_have_session_auth
from framework.exceptions import HTTPError
from framework.forms.utils import sanitize
from framework.auth.utils import parse_name

from website.models import ApiKey, User
from website.views import _render_nodes
from website import settings, filters
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
        return {
            'profile': profile_user_data,
            'user': {
                "can_edit": None,  # necessary for rendering nodes
                "is_profile": user == profile,
            },
        }

    raise HTTPError(http.NOT_FOUND)


def profile_view():
    return _profile_view()


def profile_view_id(uid):
    return _profile_view(uid)


@must_be_logged_in
def edit_profile(**kwargs):
    user = kwargs['user']

    form = request.form

    response_data = {'response' : 'success'}
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
                    'helpText': 'The field below is your full name and the name that will be '
                                'displayed in your profile. We are also '
                                'generating common citation formats for your '
                                'work using the Citation Style Language '
                                'definition. You can use the "Guess fields below" button '
                                'or edit them directly in order to accurately generate '
                                'citations.',
                },
                {
                    'id': 'impute',
                    'type': 'htmlfield',
                    'label': '',
                    'content': '<button id="profile-impute" class="btn btn-default">Guess fields below</button>',
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

    user = kwargs['user']

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

        if addon.config.has_user_settings:
            addon_enabled_settings.append(addon.config.short_name)

    rv['addon_categories'] = settings.ADDON_CATEGORIES
    rv['addons_available'] = [
        addon
        for addon in settings.ADDONS_AVAILABLE
        if 'user' in addon.owners
    ]
    rv['addons_enabled'] = addons_enabled
    rv['addon_enabled_settings'] = addon_enabled_settings

    return rv


@must_be_logged_in
def profile_addons(**kwargs):
    user = kwargs['user']
    return {
        'user_id': user._primary_key,
    }


@must_be_logged_in
def user_choose_addons(**kwargs):
    user = kwargs['user']
    user.config_addons(request.json)


@must_be_logged_in
def get_keys(**kwargs):
    user = kwargs['user']
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
    user = get_current_user()
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
    user = get_current_user()
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


@must_have_session_auth
@must_be_logged_in
def parse_names(**kwargs):
    name = request.json.get('fullname', '')
    return parse_name(name)


@must_have_session_auth
@must_be_logged_in
def post_names(**kwargs):
    user = kwargs['user']
    user.fullname = request.json['fullname']
    user.given_name = request.json['given_name']
    user.middle_names = request.json['middle_names']
    user.family_name = request.json['family_name']
    user.suffix = request.json['suffix']
    user.save()
