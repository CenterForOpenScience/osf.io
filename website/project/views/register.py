# -*- coding: utf-8 -*-
import json
import httplib as http


from flask import request
from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.exceptions import HTTPError
from framework.forms.utils import process_payload, unprocess_payload
from framework.mongo.utils import to_mongo

from website.project.decorators import (
    must_be_valid_project, must_be_contributor_or_public,
    must_have_permission, must_not_be_registration,
    must_be_public_registration
)
from website.project.metadata.schemas import OSF_META_SCHEMAS
from website.project.utils import serialize_node
from website.util.permissions import ADMIN, READ
from website.models import MetaSchema
from website import language

from .node import _view_project
from .. import clean_template_name


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
@must_have_permission(ADMIN)
@must_be_public_registration
def node_registration_retraction(auth, **kwargs):
    """ Handles retraction of public registrations

    :param auth: Authentication object for User

    :return: Template for GET, redirect URL for successful POST
    """

    node = kwargs['node'] or kwargs['project']

    if request.method == 'POST':

        data = request.json
        node.is_retracted = True
        node.retracted_justification = data['justification']
        node.save()

        url = '/project/{0}/'.format(node._id)
        ret = {'redirectUrl': url}
        return ret

    ret = _view_project(node, auth, primary=True)
    return ret

@must_be_valid_project
@must_have_permission(READ)
def node_registration_retracted(auth, **kwargs):
    """ Handles view of retracted public registrations """

    node = kwargs['node'] or kwargs['project']
    ret = serialize_node(node, auth=auth)
    return ret

@must_be_valid_project
@must_be_contributor_or_public
def node_register_template_page(auth, **kwargs):

    node = kwargs['node'] or kwargs['project']

    template_name = kwargs['template'].replace(' ', '_')
    # Error to raise if template can't be found
    not_found_error = HTTPError(
        http.NOT_FOUND,
        data=dict(
            message_short='Template not found.',
            message_long='The registration template you entered '
                         'in the URL is not valid.'
        )
    )

    if node.is_registration and node.registered_meta:
        registered = True
        payload = node.registered_meta.get(to_mongo(template_name))
        payload = json.loads(payload)
        payload = unprocess_payload(payload)

        if node.registered_schema:
            meta_schema = node.registered_schema
        else:
            try:
                meta_schema = MetaSchema.find_one(
                    Q('name', 'eq', template_name) &
                    Q('schema_version', 'eq', 1)
                )
            except NoResultsFound:
                raise not_found_error
    else:
        # Anyone with view access can see this page if the current node is
        # registered, but only admins can view the registration page if not
        # TODO: Test me @jmcarp
        if not node.has_permission(auth.user, ADMIN):
            raise HTTPError(http.FORBIDDEN)
        registered = False
        payload = None
        metaschema_query = MetaSchema.find(
            Q('name', 'eq', template_name)
        ).sort('-schema_version')
        if metaschema_query:
            meta_schema = metaschema_query[0]
        else:
            raise not_found_error
    schema = meta_schema.schema

    # TODO: Notify if some components will not be registered

    rv = {
        'template_name': template_name,
        'schema': json.dumps(schema),
        'metadata_version': meta_schema.metadata_version,
        'schema_version': meta_schema.schema_version,
        'registered': registered,
        'payload': payload,
        'children_ids': node.nodes._to_primary_keys(),
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
