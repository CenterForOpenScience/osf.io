# -*- coding: utf-8 -*-
import httplib as http
import logging

from mako.template import Template

import framework
from framework import request, User
from framework.auth.decorators import collect_auth
from framework.exceptions import HTTPError
from ..decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor
from framework.email.tasks import send_email

from website import settings
from website.filters import gravatar
from website.models import Node
from website.profile import utils
from website import hmac

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

# TODO: finish me
INVITE_EMAIL_SUBJECT = 'You have been added as a contributor to an OSF project.'
INVITE_EMAIL = Template(u'''
Hello ${new_user.fullname},

You have been added by ${referrer.fullname} as a contributor to project
"${node.title}" on the Open Science Framework. To set a password for your account,
visit:

${claim_url}

Once you have set a password you will be able to make contributions to
${node.title}.

If you have

Sincerely,

The OSF Team
''')

def email_invite(to_addr, new_user, referrer, node):
    claim_url = new_user.get_claim_url(node._primary_key)
    message = INVITE_EMAIL.render(new_user=new_user, referrer=referrer, node=node,
        claim_url=claim_url)
    logger.debug('Sending invite email:')
    logger.debug(message)
    # Don't use ttls and auth if in dev mode
    ttls = login = not settings.DEV_MODE
    return send_email.delay(
        settings.FROM_EMAIL,
        to_addr=to_addr,
        subject=INVITE_EMAIL_SUBJECT,
        message=message,
        mimetype='plain',
        ttls=ttls, login=login
    )

@must_be_valid_project
@must_be_contributor
@must_not_be_registration
def invite_contributor_post(**kwargs):
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    fullname, email = request.json.get('fullname'), request.json.get('email')
    if not fullname:
        return {'status': 400, 'message': 'Must provide fullname and email'}, 400
    new_user = User.create_unregistered(fullname=fullname, email=email)
    new_user.add_unclaimed_record(node=node,
        given_name=fullname, referrer=auth.user)
    new_user.save()
    if email:
        email_invite(email, new_user, referrer=auth.user, node=node)
    return {'status': 'success', 'contributor': _add_contributor_json(new_user)}
