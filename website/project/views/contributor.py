
from framework import request, User
from ..decorators import must_not_be_registration, must_be_valid_project, \
    must_be_contributor, must_be_contributor_or_public
from framework.auth import must_have_session_auth, get_api_key
from framework.forms.utils import sanitize
import hashlib

from framework import HTTPError
import httplib as http

@must_be_contributor_or_public
def get_contributors(*args, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']

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
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_removecontributor(*args, **kwargs):

    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']

    node_to_use = node or project

    if request.json['id'].startswith('nr-'):
        outcome = node_to_use.remove_nonregistered_contributor(
            user, request.json['name'], request.json['id'].replace('nr-', '')
        )
    else:
        outcome = node_to_use.remove_contributor(
            user, request.json['id']
        )

    if outcome:
        return {'status' : 'success'}
    raise HTTPError(http.BAD_REQUEST)
    # return {'status' : 'success' if outcome else 'failure'}

@must_have_session_auth # returns user
@must_be_valid_project # returns project
@must_be_contributor # returns user, project
@must_not_be_registration
def project_addcontributor_post(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    api_key = get_api_key()

    node_to_use = node or project

    if "user_id" in request.form:
        user_id = request.form['user_id'].strip()
        added_user = User.load(user_id)
        if added_user:
            if user_id not in node_to_use.contributors:
                node_to_use.contributors.append(added_user)
                node_to_use.contributor_list.append({'id':added_user._primary_key})
                node_to_use.save()

                node_to_use.add_log(
                    action='contributor_added',
                    params={
                        'project':node_to_use.node__parent[0]._primary_key if node_to_use.node__parent else None,
                        'node':node_to_use._primary_key,
                        'contributors':[added_user._primary_key],
                    },
                    user=user,
                    api_key=api_key
                )
    elif "email" in request.form and "fullname" in request.form:
        # TODO: Nothing is done here to make sure that this looks like an email.
        # todo have same behavior as wtforms
        email = sanitize(request.form["email"].strip())
        fullname = sanitize(request.form["fullname"].strip())
        if email and fullname:
            node_to_use.contributor_list.append({'nr_name':fullname, 'nr_email':email})
            node_to_use.save()

        node_to_use.add_log(
            action='contributor_added',
            params={
                'project':node_to_use.node__parent[0]._primary_key if node_to_use.node__parent else None,
                'node':node_to_use._primary_key,
                'contributors':[{"nr_name":fullname, "nr_email":email}],
            },
            user=user,
            api_key=api_key
        )

    return {'status' : 'success'}, 201
