
import os
import json
import logging

from framework import request, status
from framework.auth import must_have_session_auth
from ..decorators import must_not_be_registration, must_be_valid_project, must_be_contributor, must_be_contributor_or_public
from framework.forms.utils import sanitize
from .node import _view_project

from website.models import MetaSchema
from framework import Q

from .. import clean_template_name

logger = logging.getLogger(__name__)

@must_have_session_auth
@must_be_valid_project
@must_be_contributor # returns user, project
@must_not_be_registration
def node_register_page(*args, **kwargs):

    user = kwargs['user']
    node_to_use = kwargs['node'] or kwargs['project']

    rv = {
        'options': [
            {
                'template_name': metaschema._id,
                'template_name_clean': clean_template_name(metaschema._id)
            }
            for metaschema in MetaSchema.find(Q('category', 'eq', 'registration'))
        ]
    }
    rv.update(_view_project(node_to_use, user))
    return rv


@must_have_session_auth
@must_be_valid_project
@must_be_contributor_or_public # returns user, project
def node_register_template_page(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']

    node_to_use = node or project

    template_name = kwargs['template'].replace(' ', '_').replace('.txt', '')

    meta_schema = MetaSchema.find_one(Q('_id', 'eq', template_name))
    schema = meta_schema.schema

    if node_to_use.is_registration and node_to_use.registered_meta:
        registered = True
        payload = json.loads(node_to_use.registered_meta.get(template_name))
        for page in schema['pages']:
            for question in page['questions']:
                question['value'] = payload.get(question['id'], '')

    else:
        registered = False

    rv = {
        'template_name': template_name,
        'schema': json.dumps(schema),
        'registered': registered,
    }
    rv.update(_view_project(node_to_use, user))
    return rv

@must_have_session_auth
@must_be_valid_project
@must_be_contributor # returns user, project
@must_not_be_registration
def node_register_template_page_post(*args, **kwargs):
    project = kwargs['project']
    node = kwargs['node']
    user = kwargs['user']
    api_key = kwargs['api_key']

    node_to_use = node or project
    data = request.json

    for k, v in data.items():
        if v is not None and v != sanitize(v):
            # todo interface needs to deal with this
            status.push_status_message('Invalid submission.')
            return json.dumps({
                'status': 'error',
            })

    template = kwargs['template']
    # TODO: Using json.dumps because node_to_use.registered_meta's values are
    # expected to be strings (not dicts). Eventually migrate all these to be
    # dicts, as this is unnecessary
    register = node_to_use.register_node(user, api_key, template, json.dumps(data))

    return {
        'status': 'success',
        'result': register.url,
    }, 201
