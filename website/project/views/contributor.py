# -*- coding: utf-8 -*-
import httplib as http
import logging

from mako.template import Template
from itsdangerous import BadSignature

import framework
from framework import request, User
from framework.auth.decorators import collect_auth
from framework.auth.utils import parse_name
from framework.exceptions import HTTPError
from ..decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor
from framework.email.tasks import send_email
from framework import forms
from framework.auth.forms import SetEmailAndPasswordForm

from website import settings, mails
from website.filters import gravatar
from website.models import Node
from website.profile import utils


logger = logging.getLogger(__name__)


@collect_auth
@must_be_valid_project
def get_node_contributors_abbrev(**kwargs):

    auth = kwargs.get('auth')
    node_to_use = kwargs['node'] or kwargs['project']

    max_count = kwargs.get('max_count', 3)
    if 'user_ids' in kwargs:
        users = [
            User.load(user_id) for user_id in kwargs['user_ids']
            if user_id in node_to_use.contributors
        ]
    else:
        users = node_to_use.contributors

    if not node_to_use.can_view(auth):
        raise HTTPError(http.FORBIDDEN)

    contributors = []

    n_contributors = len(users)
    others_count, others_suffix = '', ''

    for index, user in enumerate(users[:max_count]):

        if index == max_count - 1 and len(users) > max_count:
            separator = ' &'
            others_count = n_contributors - 3
            others_suffix = 's' if others_count > 1 else ''
        elif index == len(users) - 1:
            separator = ''
        elif index == len(users) - 2:
            separator = ' &'
        else:
            separator = ','

        contributors.append({
            'user_id': user._primary_key,
            'separator': separator,
        })

    return {
        'contributors': contributors,
        'others_count': others_count,
        'others_suffix': others_suffix,
    }


def _add_contributor_json(user):

    return {
        'fullname': user.fullname,
        'id': user._primary_key,
        'registered': user.is_registered,
        'active': user.is_active(),
        'gravatar': gravatar(
            user, use_ssl=True,
            size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR
        )
    }


def _jsonify_contribs(contribs):

    data = []
    for contrib in contribs:
        if 'id' in contrib:
            user = User.load(contrib['id'])
            if user is None:
                logger.error('User {} not found'.format(contrib['id']))
                continue
            data.append(utils.serialize_user(user))
        else:
            data.append(utils.serialize_unreg_user(contrib))
    return data


@collect_auth
@must_be_valid_project
def get_contributors(**kwargs):

    auth = kwargs.get('auth')
    node_to_use = kwargs['node'] or kwargs['project']

    if not node_to_use.can_view(auth):
        raise HTTPError(http.FORBIDDEN)

    contribs = _jsonify_contribs(node_to_use.contributor_list)
    return {'contributors': contribs}


@collect_auth
@must_be_valid_project
def get_contributors_from_parent(**kwargs):

    auth = kwargs.get('auth')
    node_to_use = kwargs['node'] or kwargs['project']

    parent = node_to_use.node__parent[0] if node_to_use.node__parent else None
    if not parent:
        raise HTTPError(http.BAD_REQUEST)

    if not node_to_use.can_view(auth):
        raise HTTPError(http.FORBIDDEN)

    contribs = [
        _add_contributor_json(contrib)
        for contrib in parent.contributors
        if contrib not in node_to_use.contributors
    ]

    return {'contributors': contribs}


@must_be_contributor
def get_recently_added_contributors(**kwargs):

    auth = kwargs.get('auth')
    node_to_use = kwargs['node'] or kwargs['project']

    if not node_to_use.can_view(auth):
        raise HTTPError(http.FORBIDDEN)

    contribs = [
        _add_contributor_json(contrib)
        for contrib in auth.user.recently_added
        if contrib not in node_to_use.contributors
    ]

    return {'contributors': contribs}


@must_be_valid_project  # returns project
@must_be_contributor  # returns user, project
@must_not_be_registration
def project_before_remove_contributor(**kwargs):

    node_to_use = kwargs['node'] or kwargs['project']

    contributor = User.load(request.json.get('id'))
    prompts = node_to_use.callback(
        'before_remove_contributor', removed=contributor,
    )

    return {'prompts': prompts}


@must_be_valid_project  # returns project
@must_be_contributor  # returns user, project
@must_not_be_registration
def project_removecontributor(**kwargs):

    node_to_use = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']

    if request.json['id'].startswith('nr-'):
        outcome = node_to_use.remove_nonregistered_contributor(
            auth, request.json['name'],
            request.json['id'].replace('nr-', '')
        )
    else:
        contributor = User.load(request.json['id'])
        if contributor is None:
            raise HTTPError(http.BAD_REQUEST)
        outcome = node_to_use.remove_contributor(
            contributor=contributor, auth=auth,
        )
    if outcome:
        framework.status.push_status_message('Contributor removed', 'info')
        return {'status': 'success'}
    raise HTTPError(http.BAD_REQUEST)


@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_addcontributors_post(**kwargs):
    """ Add contributors to a node. """

    node_to_use = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    user_ids = request.json.get('user_ids', [])
    node_ids = request.json.get('node_ids', [])
    users = [
        User.load(user_id)
        for user_id in user_ids
    ]
    node_to_use.add_contributors(contributors=users, auth=auth)
    node_to_use.save()
    for node_id in node_ids:
        node = Node.load(node_id)
        node.add_contributors(contributors=users, auth=auth)
        node.save()
    return {'status': 'success'}, 201

def email_invite(to_addr, new_user, referrer, node):
    """Send an invite mail to an unclaimed user.

    :param str to_addr: The email address to send to.
    :param User new_user: The User record for the unclaimed user.
    :param User referrer: The User record for the referring user.
    :param Node node: The project or component that the new user was added to.
    """
    # Add querystring with email, so that set password form can prepopulate the
    # email field
    claim_url = new_user.get_claim_url(node._primary_key) + '?email={0}'.format(to_addr)
    return mails.send_mail(to_addr, mails.INVITE, user=new_user, referrer=referrer,
        claim_url=claim_url)


def claim_user_form(**kwargs):
    """View for rendering the set password page for a claimed user.

    Renders the set password form, validates it, and sets the user's password.
    """
    # There shouldn't be a user logged in
    if framework.auth.get_current_user():
        # TODO: should display more useful info to the user instead of an error page
        raise HTTPError(400)
    signature = kwargs['signature']
    email = request.args.get('email', '')
    form = SetEmailAndPasswordForm(request.form)
    # Parse the signature; if invalid, raise 404
    try:
        referral_data = User.parse_claim_signature(signature)
    except BadSignature:

        raise HTTPError(http.NOT_FOUND)
    user = framework.auth.get_user(id=referral_data['_id'])
    # user ID is invalid. Unregistered user is not in database
    if not user:
        raise HTTPError(400)
    parsed_name = parse_name(referral_data['name'])
    if request.method == 'POST':
        if form.validate():
            username = form.username.data.strip()
            password = form.password.data.strip()
            user.register(username=username, password=password)
            user.save()
            project_id = referral_data['project_id']
            # Go to project page
            return framework.redirect('/{project_id}/'.format(project_id=project_id))
        else:
            forms.push_errors_to_status(form.errors)
    return {
        'firstname': parsed_name['given_name'],
        'email': email,
        'fullname': referral_data['name']
    }

@must_be_valid_project
@must_be_contributor
@must_not_be_registration
def invite_contributor_post(**kwargs):
    """API view for inviting an unregistered user.
    Expects JSON arguments with 'fullname' (required) and email (not required)
    Creates a new unregistered user in the database.
    If email is provided, emails the invited user.
    """
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    fullname, email = request.json.get('fullname'), request.json.get('email')
    if not fullname:
        return {'status': 400, 'message': 'Must provide fullname'}, 400
    new_user = framework.auth.get_user(username=email)
    if not new_user:
        new_user = User.create_unregistered(fullname=fullname, email=email)
        new_user.save()  # Need to save so that user has an ID
    else:
        return {'status': 400, 'message': 'User is already in database'}, 400
    if node._primary_key not in new_user.unclaimed_records:
        new_user.add_unclaimed_record(node=node,
            given_name=fullname, referrer=auth.user)
        new_user.save()
    else:
        return {'status': 400, 'message': 'User is already a contributor to this project.'}, 400
    if email:
        email_invite(email, new_user, referrer=auth.user, node=node)
    return {'status': 'success', 'contributor': _add_contributor_json(new_user)}
