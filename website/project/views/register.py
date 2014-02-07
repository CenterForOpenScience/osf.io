# -*- coding: utf-8 -*-
import json
import logging

from framework import request
from ..decorators import must_not_be_registration, must_be_valid_project, must_be_contributor, must_be_contributor_or_public
from framework.forms.utils import process_payload
from framework.mongo.utils import to_mongo
from .node import _view_project

from website.project.metadata.schemas import OSF_META_SCHEMAS

from website.models import MetaSchema
from framework import Q

from .. import clean_template_name

logger = logging.getLogger(__name__)

@must_be_valid_project
@must_be_contributor # returns user, project
@must_not_be_registration
def node_register_page(*args, **kwargs):

    auth = kwargs['auth']
    node_to_use = kwargs['node'] or kwargs['project']

    rv = {
        'options': [
            {
                'template_name': metaschema['name'],
                'template_name_clean': clean_template_name(metaschema['name'])
            }
            for metaschema in OSF_META_SCHEMAS
        ]
    }
    rv.update(_view_project(node_to_use, auth, primary=True))
    return rv


@must_be_valid_project
@must_be_contributor_or_public # returns user, project
def node_register_template_page(*args, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']
    link = kwargs['link']
    auth = kwargs['auth']

    template_name = kwargs['template']\
        .replace(' ', '_')

    if node_to_use.is_registration and node_to_use.registered_meta:
        registered = True
        payload = node_to_use.registered_meta.get(to_mongo(template_name))
        if node_to_use.registered_schema:
            meta_schema = node_to_use.registered_schema
        else:
            meta_schema = MetaSchema.find_one(
                Q('name', 'eq', template_name) &
                Q('schema_version', 'eq', 1)
            )
    else:
        registered = False
        payload = None
        meta_schema = MetaSchema.find(
            Q('name', 'eq', template_name)
        ).sort('-schema_version')[0]

    schema = meta_schema.schema

    # TODO: Notify if some components will not be registered

    rv = {
        'template_name': template_name,
        'schema': json.dumps(schema),
        'metadata_version': meta_schema.metadata_version,
        'schema_version': meta_schema.schema_version,
        'registered': registered,
        'payload': payload,
    }
    rv.update(_view_project(node_to_use, auth, link, primary=True))
    return rv


@must_be_valid_project  # returns project
@must_be_contributor  # returns user, project
@must_not_be_registration
def project_before_register(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = kwargs['auth'].user

    prompts = node.callback('before_register', node, user)

    return {'prompts': prompts}


@must_be_valid_project
@must_be_contributor # returns user, project
@must_not_be_registration
def node_register_template_page_post(*args, **kwargs):

    node_to_use = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']

    data = request.json

    # Sanitize payload data
    clean_data = process_payload(data)

    template = kwargs['template']
    # TODO: Using json.dumps because node_to_use.registered_meta's values are
    # expected to be strings (not dicts). Eventually migrate all these to be
    # dicts, as this is unnecessary
    schema = MetaSchema.find(
        Q('name', 'eq', template)
    ).sort('-schema_version')[0]
    register = node_to_use.register_node(
        schema, auth, template, json.dumps(clean_data),
    )

    return {
        'status': 'success',
        'result': register.url,
    }, 201
