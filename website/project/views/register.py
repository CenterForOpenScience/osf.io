# -*- coding: utf-8 -*-
import json
import httplib as http

from flask import request
from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.exceptions import HTTPError
from framework.mongo.utils import to_mongo
from framework.forms.utils import process_payload, unprocess_payload

from website import settings
from website.project.decorators import (
    must_be_valid_project, must_be_contributor_or_public,
    must_have_permission, must_not_be_registration
)
from website.project.metadata.schemas import OSF_META_SCHEMAS
from website.util.permissions import ADMIN
from website.models import MetaSchema
from website.models import NodeLog
from website import language

from website.identifiers.client import EzidClient
from website.identifiers.client import ClientError

from .node import _view_project
from .. import clean_template_name


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def node_register_page(auth, **kwargs):

    node = kwargs['node'] or kwargs['project']

    ret = {
        'options': [
            {
                'template_name': metaschema['name'],
                'template_name_clean': clean_template_name(metaschema['name'])
            }
            for metaschema in OSF_META_SCHEMAS
        ]
    }
    ret.update(_view_project(node, auth, primary=True))
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

    ret = {
        'template_name': template_name,
        'schema': json.dumps(schema),
        'metadata_version': meta_schema.metadata_version,
        'schema_version': meta_schema.schema_version,
        'registered': registered,
        'payload': payload,
        'children_ids': node.nodes._to_primary_keys(),
    }
    ret.update(_view_project(node, auth, primary=True))
    return ret


@must_be_valid_project  # returns project
@must_have_permission(ADMIN)
@must_not_be_registration
def project_before_register(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    user = auth.user

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


def _get_or_create_identifiers(doi, metadata):
    client = EzidClient('apitest', 'apitest')
    try:
        resp = client.create_identifier(doi, metadata)
        return dict(
            pair.strip().split(':')
            for pair in resp['success'].split('|')
        )
    except ClientError as error:
        if 'identifier already exists' not in error.message.lower():
            raise
        resp = client.get_identifier(doi)
        doi = resp['success']
        suffix = doi.strip(settings.DOI_NAMESPACE)
        return {
            'doi': doi,
            'ark': '{0}{1}'.format(settings.ARK_NAMESPACE, suffix),
        }


@must_be_valid_project
@must_have_permission(ADMIN)
def node_identifiers(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    if not node.is_registration or not node.is_public or node.parent_node:
        raise HTTPError(http.BAD_REQUEST)
    if request.method == 'GET':
        return {
            'doi': node.get_identifier_value('doi'),
            'ark': node.get_identifier_value('ark'),
        }
    elif request.method == 'POST':
        if node.get_identifier('doi') or node.get_identifier('ark'):
            raise HTTPError(http.BAD_REQUEST)
        doi = '{0}{1}'.format(settings.DOI_NAMESPACE, node._id)
        metadata = {
            'datacite.creator': node.creator.fullname,
            'datacite.title': node.title,
            'datacite.publisher': 'Open Science Framework',
            'datacite.publicationyear': str(node.registered_date.year),
        }
        try:
            identifiers = _get_or_create_identifiers(doi, metadata)
        except ClientError:
            raise HTTPError(http.BAD_REQUEST)
        for category, value in identifiers.iteritems():
            node.set_identifier_value(category, value)
        node.add_log(
            NodeLog.EXTERNAL_IDS_ADDED,
            params={
                'project': node.parent_id,
                'node': node._id,
                'identifiers': identifiers,
            },
            auth=auth,
        )
        return identifiers, http.CREATED
