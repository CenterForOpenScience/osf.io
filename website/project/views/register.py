
from framework import request, push_status_message
from framework.auth import must_have_session_auth
from ..decorators import must_not_be_registration, must_be_valid_project, must_be_contributor
from framework.forms.utils import sanitize
from .node import _view_project

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

    content = ','.join([
        '"{}"'.format(clean_template_name(template_name))
        for template_name in os.listdir('website/static/registration_templates/')
    ])
    rv = {
        'content' : content,
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

    with open('website/static/registration_templates/' +  template_name + '.txt') as f:
        template = f.read()

    content = ','.join([
        '"{}"'.format(stored_template_name.replace('_', ' '))
        for stored_template_name in os.listdir('website/static/registration_templates/')
    ])

    if node_to_use.is_registration and node_to_use.registered_meta:
        form_values = node_to_use.registered_meta.get(template_name)
    else:
        form_values = None

    rv = {
        'content' : content,
        'template' : template,
        'template_name' : template_name,
        'form_values' : form_values
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

    node_to_use = node or project

    data = request.form['data']
    parsed_data = json.loads(data)

    for k, v in parsed_data.items():
        if v is not None and v != sanitize(v):
            # todo interface needs to deal with this
            push_status_message('Invalid submission.')
            return json.dumps({
                'status' : 'error',
            })

    template = kwargs['template']

    register = node_to_use.register_node(user, template, data)

    # todo return 201
    return {
        'status' : 'success',
        'result' : register.url(),
    }
