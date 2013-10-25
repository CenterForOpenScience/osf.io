# -*- coding: utf-8 -*-
import httplib as http
import logging

from framework import request, User, Q
from ..decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor, must_be_contributor_or_public
from framework.auth import must_have_session_auth, get_current_user, get_api_key
from framework.forms.utils import sanitize
import hashlib
import json

from framework import HTTPError

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

@must_be_valid_project
def get_contributors(*args, **kwargs):

    user = get_current_user()
    api_key = get_api_key()
    node_to_use = kwargs['node'] or kwargs['project']

    if not node_to_use.can_edit(user, api_key) \
            and not node_to_use.are_contributors_public:
        raise HTTPError(http.FORBIDDEN)

    contributors = []
    for contributor in node_to_use.contributor_list:
        if 'id' in contributor:
            user = User.load(contributor['id'])
            contributors.append({
                'registered' : True,
                'id' : user._primary_key,
                'fullname' : user.fullname,
            })
        else:
            contributors.append({
                'registered' : False,
                'id' : hashlib.md5(contributor['nr_email']).hexdigest(),
                'fullname' : contributor['nr_name'],
            })

    return {'contributors' : contributors}


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
        # TODO(sloria): Add flash message
        return {'status': 'success'}
    raise HTTPError(http.BAD_REQUEST)

# TODO: This should accept json--not form--data
@must_have_session_auth # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_addcontributors_post(*args, **kwargs):
    """ Add contributors to a node. """

    node_to_use = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    api_key = get_api_key()
    user_ids_json = request.form.get('user_ids')
    user_ids = json.loads(user_ids_json)
    # TODO: Move to model

    for user_id in user_ids:
        if user_id not in node_to_use.contributors:
            added_user = User.load(user_id)
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
            'contributors': user_ids,
        },
        user=user,
        api_key=api_key,
    )

    return {'status': 'success'}, 201
