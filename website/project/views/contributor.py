# -*- coding: utf-8 -*-
import httplib as http
import hashlib
import logging

import framework
from framework import request, User, Q
from framework.exceptions import HTTPError
from ..decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor, must_be_contributor_or_public
from framework.auth import must_have_session_auth, get_current_user, get_api_key


from website import settings
from website.filters import gravatar
from website.models import Node

logger = logging.getLogger(__name__)


@must_be_valid_project
def get_node_contributors_abbrev(*args, **kwargs):

    user = get_current_user()
    api_key = get_api_key()
    node_to_use = kwargs['node'] or kwargs['project']

    max_count = kwargs.get('max_count', 3)
    if 'user_ids' in kwargs:
        user_ids = [
            user for user in kwargs['user_ids']
            if user in node_to_use.contributors
        ]
    else:
        user_ids = node_to_use.contributors

    if not node_to_use.can_edit(user, api_key) \
            and not node_to_use.are_contributors_public:
        raise HTTPError(http.FORBIDDEN)

    contributors = []

    n_contributors = len(user_ids)
    others_count, others_suffix = '', ''

    for index, user_id in enumerate(user_ids[:max_count]):

        if index == max_count - 1 and len(user_ids) > max_count:
            separator = ' &'
            others_count = n_contributors - 3
            others_suffix = 's' if others_count > 1 else ''
        elif index == len(user_ids) - 1:
            separator = ''
        elif index == len(user_ids) - 2:
            separator = ' &'
        else:
            separator = ','

        contributors.append({
            'user_id': user_id,
            'separator': separator,
        })

    return {
        'contributors': contributors,
        'others_count': others_count,
        'others_suffix': others_suffix,
    }


def _jsonify_contribs(contribs):

    data = []
    # TODO(sloria): Put into User.serialize()
    for contrib in contribs:
        if 'id' in contrib:
            user = User.load(contrib['id'])
            data.append({
                'registered': True,
                'id': user._primary_key,
                'fullname': user.fullname,
                'gravatar': gravatar(
                    user,
                    use_ssl=True,
                    size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR
                ),
            })
        else:
            contribs.append({
                'registered': False,
                'id': hashlib.md5(contrib['nr_email']).hexdigest(),
                'fullname': contrib['nr_name'],
            })

    return data


@must_be_valid_project
def get_contributors(*args, **kwargs):

    user = get_current_user()
    api_key = get_api_key()
    node_to_use = kwargs['node'] or kwargs['project']

    if not node_to_use.can_edit(user, api_key) \
            and not node_to_use.are_contributors_public:
        raise HTTPError(http.FORBIDDEN)

    contribs = _jsonify_contribs(node_to_use.contributor_list)

    return {'contributors': contribs}


@must_be_valid_project
def get_contributors_from_parent(*args, **kwargs):

    user = get_current_user()
    api_key = get_api_key()
    node_to_use = kwargs['node'] or kwargs['project']

    parent = node_to_use.node__parent[0] if node_to_use.node__parent else None
    if not parent:
        raise HTTPError(http.BAD_REQUEST)

    if not node_to_use.can_edit(user, api_key) or \
            not parent.can_edit(user, api_key):
        raise HTTPError(http.FORBIDDEN)

    contribs = _jsonify_contribs([
        contrib
        for contrib in parent.contributor_list
        if contrib not in node_to_use.contributor_list
    ])

    return {'contributors': contribs}


@must_have_session_auth
@must_be_valid_project  # returns project
@must_be_contributor  # returns user, project
@must_not_be_registration
def project_removecontributor(*args, **kwargs):

    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    api_key = get_api_key()
    node_to_use = node or project

    # FIXME: this isn't working
    if request.json['id'].startswith('nr-'):
        outcome = node_to_use.remove_nonregistered_contributor(
            user, request.json['name'], request.json['id'].replace('nr-', '')
        )
    else:
        try:
            contributor = User.find_one(Q("_id", "eq", request.json['id']))
        except Exception as err:
            logger.error(err)
            raise HTTPError(http.BAD_REQUEST)
        outcome = node_to_use.remove_contributor(
            user, contributor, api_key=api_key
        )
    if outcome:
        framework.status.push_status_message("Contributor removed", "info")
        return {'status': 'success'}
    raise HTTPError(http.BAD_REQUEST)


def _add_contributors(node_to_use, users_to_add, user, api_key):

    for added_user in users_to_add:
        if added_user not in node_to_use.contributors:
            node_to_use.contributors.append(added_user)
            node_to_use.contributor_list.append({
                'id': added_user._primary_key,
            })
    node_to_use.save()

    node_to_use.add_log(
        action='contributor_added',
        params={
            'project': node_to_use.parent_id,
            'node': node_to_use._primary_key,
            'contributors': [added_user._id for added_user in users_to_add],
        },
        user=user,
        api_key=api_key,
    )


@must_have_session_auth # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_addcontributors_post(*args, **kwargs):
    """ Add contributors to a node. """

    node_to_use = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    api_key = get_api_key()
    user_ids = request.json.get('user_ids', [])
    node_ids = request.json.get('node_ids', [])
    # TODO: Move to model

    users = [
        User.load(user_id)
        for user_id in user_ids
    ]

    status = _add_contributors(
        node_to_use, users, user, api_key
    )

    for node_id in node_ids:
        node = Node.load(node_id)
        status = _add_contributors(
            node, users, user, api_key
        )

    return {'status': 'success'}, 201
