
from framework import request, push_status_message
from framework.auth import must_have_session_auth
from ..decorators import must_not_be_registration, must_be_valid_project, must_be_contributor
from framework.forms.utils import sanitize
from .node import _view_project

from website.models import MetaSchema
from framework import Q

from .. import clean_template_name

import os
import json

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
@must_be_contributor # returns user, project
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
        for item in schema:
            item['value'] = payload[item['id']]
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

    data = request.form['data']
    parsed_data = json.loads(data)

    for k, v in parsed_data.items():
        if v is not None and v != sanitize(v):
            # todo interface needs to deal with this
            push_status_message('Invalid submission.')
            return json.dumps({
                'status': 'error',
            })

    template = kwargs['template']

    register = node_to_use.register_node(user, api_key, template, data)

    print register.url
    return {
        'status': 'success',
        'result': register.url,
    }, 201
