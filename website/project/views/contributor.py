# -*- coding: utf-8 -*-
import httplib as http
import logging

import framework
from framework import request, User, status
from framework.auth.decorators import collect_auth
from framework.auth.utils import parse_name
from framework.exceptions import HTTPError
from ..decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor, must_be_contributor_or_public
from framework import forms
from framework.auth.forms import SetEmailAndPasswordForm
from framework.auth.exceptions import DuplicateEmailError

from website import settings, mails, language
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

# TODO: Almost identical to utils.serialize_user. Remove duplication.
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


def serialized_contributors(node):

    data = []
    for contrib in node.contributors:
        serialized = utils.serialize_user(contrib)
        serialized['fullname'] = contrib.display_full_name(node=node)
        data.append(serialized)
    return data


@collect_auth
@must_be_valid_project
def get_contributors(**kwargs):

    auth = kwargs.get('auth')
    node = kwargs['node'] or kwargs['project']

    if not node.can_view(auth):
        raise HTTPError(http.FORBIDDEN)

    contribs = serialized_contributors(node)
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
        if contrib.is_active()
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


def send_claim_email(email, user, node):
    """Send an email for claiming a user account. Either sends to the given email
    or the referrer's email, depending on the email address provided.

    :param str email: The address given in the claim user form
    :param User user: The User record to claim.
    :param Node node: The node where the user claimed their account.
    """
    unclaimed_record = user.get_unclaimed_record(node._primary_key)
    referrer = User.load(unclaimed_record['referrer_id'])
    claim_url = user.get_claim_url(node._primary_key, external=True) + '?email={0}'.format(email)
    # If given email is the same provided by user, just send to that email
    if unclaimed_record.get('email', None) == email.lower().strip():
        mail_tpl = mails.INVITE
        to_addr = email
    else:  # Otherwise have the referrer forward the email to the user
        mail_tpl = mails.FORWARD_INVITE
        to_addr = referrer.username
    return mails.send_mail(to_addr, mail_tpl,
        user=user,
        referrer=referrer,
        node=node,
        claim_url=claim_url,
        email=email,
        fullname=unclaimed_record['name']
    )


def claim_user_form(**kwargs):
    """View for rendering the set password page for a claimed user.

    Renders the set password form, validates it, and sets the user's password.
    """
    uid, pid, token = kwargs['uid'], kwargs['pid'], kwargs['token']
    # There shouldn't be a user logged in
    if framework.auth.get_current_user():
        logout_url = framework.url_for('OsfWebRenderer__auth_logout')
        error_data = {'message_short': 'You are already logged in.',
            'message_long': ('To claim this account, you must first '
                '<a href={0}>log out.</a>'.format(logout_url))}
        raise HTTPError(400, data=error_data)
    user = framework.auth.get_user(id=uid)
    # user ID is invalid. Unregistered user is not in database
    if not user:
        raise HTTPError(400)
    # if token is invalid, throw an error
    if not user.verify_claim_token(token=token, project_id=pid):
        error_data = {'message_short': 'Invalid URL.',
            'message_long': 'The URL you entered is invalid.'}
        raise HTTPError(400, data=error_data)

    parsed_name = parse_name(user.fullname)
    email = request.args.get('email', '')
    form = SetEmailAndPasswordForm(request.form)
    if request.method == 'POST':
        if form.validate():
            username = form.username.data.lower().strip()
            password = form.password.data.strip()
            user.register(username=username, password=password)
            del user.unclaimed_records[pid]
            user.save()
            # Authenticate user and redirect to project page
            response = framework.redirect('/{pid}/'.format(pid=pid))
            node = Node.load(pid)
            status.push_status_message(language.CLAIMED_CONTRIBUTOR.format(node=node),
                'success')
            return framework.auth.authenticate(user, response)
        else:
            forms.push_errors_to_status(form.errors)
    return {
        'firstname': parsed_name['given_name'],
        'email': email,
        'fullname': user.fullname
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
    try:
        new_user = node.add_unregistered_contributor(email=email, fullname=fullname,
            auth=auth)
        node.save()
    except DuplicateEmailError:
        # User is in database. If they are active, raise an error. If not,
        # go ahead and send the email invite
        new_user = framework.auth.get_user(username=email)
        if new_user.is_registered:
            msg = 'User is already in database. Please go back and try your search again.'
            return {'status': 400, 'message': msg}, 400
        if node.is_contributor(new_user):
            msg = 'User with this email address is already a contributor to this project.'
            return {'status': 400, 'message': msg}, 400
    if email:
        send_claim_email(email, new_user, node)
    serialized = _add_contributor_json(new_user)
    # display correct name
    serialized['fullname'] = fullname
    return {'status': 'success', 'contributor': serialized}


@must_be_contributor_or_public
def claim_user_post(**kwargs):
    """View for claiming a user from the X-editable form on a project page.
    """
    reqdata = request.json
    user = User.load(reqdata['pk'])
    email = reqdata['value']
    node = kwargs['node'] or kwargs['project']
    send_claim_email(email, user, node)
    unclaimed_data = user.get_unclaimed_record(node._primary_key)
    return {'status': 'success', 'fullname': unclaimed_data['name']}
