# -*- coding: utf-8 -*-
import json
import logging
import httplib as http

from framework import Q
from framework import request
from framework.exceptions import HTTPError
from framework.forms.utils import process_payload, unprocess_payload
from framework.mongo.utils import to_mongo

from website.project.decorators import (
    must_be_valid_project, must_be_contributor_or_public,
    must_have_permission, must_not_be_registration
)
from website.project.metadata.schemas import OSF_META_SCHEMAS
from website.util.permissions import ADMIN
from website.models import MetaSchema
from website import language

from .node import _view_project
from .. import clean_template_name


logger = logging.getLogger(__name__)


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def node_register_page(auth, **kwargs):

    node = kwargs['node'] or kwargs['project']

    out = {
        'options': [
            {
                'template_name': metaschema['name'],
                'template_name_clean': clean_template_name(metaschema['name'])
            }
            for metaschema in OSF_META_SCHEMAS
        ]
    }
    out.update(_view_project(node, auth, primary=True))
    return out


@must_be_valid_project
@must_be_contributor_or_public
def node_register_template_page(auth, **kwargs):

    node = kwargs['node'] or kwargs['project']

    template_name = kwargs['template'].replace(' ', '_')

    if node.is_registration and node.registered_meta:
        registered = True
        payload = node.registered_meta.get(to_mongo(template_name))
        payload = json.loads(payload)
        payload = unprocess_payload(payload)
        payload = json.dumps(payload)
        if node.registered_schema:
            meta_schema = node.registered_schema
        else:
            meta_schema = MetaSchema.find_one(
                Q('name', 'eq', template_name) &
                Q('schema_version', 'eq', 1)
            )
    else:
        # Anyone with view access can see this page if the current node is
        # registered, but only admins can view the registration page if not
        # TODO: Test me @jmcarp
        if not node.has_permission(auth.user, ADMIN):
            raise HTTPError(http.FORBIDDEN)
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
    rv.update(_view_project(node, auth, primary=True))
    return rv


@must_be_valid_project  # returns project
@must_have_permission(ADMIN)
@must_not_be_registration
def project_before_register(**kwargs):

    node = kwargs['node'] or kwargs['project']
    user = kwargs['auth'].user

    prompts = node.callback('before_register', user=user)

    if node.has_pointers_recursive:
        prompts.append(
            language.BEFORE_REGISTER_HAS_POINTERS.format(
                category=node.project_or_component
            )
        )

    return {'prompts': prompts}


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def node_register_template_page_post(auth, **kwargs):

    node = kwargs['node'] or kwargs['project']
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
    register = node.register_node(
        schema, auth, template, json.dumps(clean_data),
    )

    return {
        'status': 'success',
        'result': register.url,
    }, http.CREATED
