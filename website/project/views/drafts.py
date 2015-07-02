from flask import request
import httplib as http

from modularodm import Q

from framework.mongo.utils import get_or_http_error
from framework.exceptions import HTTPError

from website.util.permissions import ADMIN
from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
)
from website.project.model import MetaSchema, DraftRegistration
from website.project.metadata.utils import serialize_meta_schema, serialize_draft_registration

get_draft_or_fail = lambda pk: get_or_http_error(DraftRegistration, pk)
get_schema_or_fail = lambda query: get_or_http_error(MetaSchema, query)

def get_all_draft_registrations(*args, **kwargs):
    count = request.args.get('count', 100)

    all_drafts = DraftRegistration.find()[:count]

    return {
        'drafts': [serialize_draft_registration(d) for d in all_drafts]
    }

@must_have_permission(ADMIN)
@must_be_valid_project
def get_draft_registration(auth, node, draft_pk, *args, **kwargs):
    draft = get_draft_or_fail(draft_pk)
    return serialize_draft_registration(draft, auth)

@must_have_permission(ADMIN)
@must_be_valid_project
def get_draft_registrations(auth, node, *args, **kwargs):

    count = request.args.get('count', 100)

    drafts = DraftRegistration.find(
        Q('initiator', 'eq', auth.user)
    )[:count]
    return {
        'drafts': [serialize_draft_registration(d, auth) for d in drafts]
    }

@must_have_permission(ADMIN)
@must_be_valid_project
def create_draft_registration(auth, node, *args, **kwargs):

    data = request.get_json()

    schema_name = data.get('schema_name')
    if not schema_name:
        raise HTTPError(http.BAD_REQUEST)

    schema_version = data.get('schema_version', 1)
    schema_data = data.get('schema_data', {})

    meta_schema = get_schema_or_fail(
        Q('name', 'eq', schema_name) &
        Q('schema_version', 'eq', schema_version)
    )
    draft = DraftRegistration(
        initiator=auth.user,
        branched_from=node,
        registration_schema=meta_schema,
        registration_metadata=schema_data
    )
    draft.save()
    return serialize_draft_registration(draft, auth), http.CREATED

@must_have_permission(ADMIN)
@must_be_valid_project
def update_draft_registration(auth, node, draft_pk, *args, **kwargs):
    data = request.get_json()

    draft = get_draft_or_fail(draft_pk)

    schema_data = data.get('schema_data', {})

    schema_name = data.get('schema_name')
    schema_version = data.get('schema_version', 1)
    if schema_name:
        meta_schema = get_schema_or_fail(
            Q('name', 'eq', schema_name) &
            Q('schema_version', 'eq', schema_version)
        )
        existing_schema = draft.registration_schema
        if (existing_schema.name, existing_schema.schema_version) != (meta_schema.name, meta_schema.schema_version):
            draft.registration_schema = meta_schema

    draft.registration_metadata.update(schema_data)
    draft.save()
    return serialize_draft_registration(draft, auth), http.OK

@must_have_permission(ADMIN)
@must_be_valid_project
def delete_draft_registration(auth, node, draft_pk, *args, **kwargs):

    if not draft_pk:
        raise HTTPError(http.BAD_REQUEST)
    DraftRegistration.remove_one(draft_pk)
    return {}, http.OK

def get_metaschemas(*args, **kwargs):

    count = request.args.get('count', 100)

    meta_schemas = MetaSchema.find()[:count]
    return {
        'meta_schemas': [
            serialize_meta_schema(ms) for ms in meta_schemas
        ]
    }, http.OK

def get_metaschema(schema_name, schema_version=1, *args, **kwargs):
    meta_schema = get_schema_or_fail(
        Q('name', 'eq', schema_name) &
        Q('schema_version', 'eq', schema_version)
    )
    return serialize_meta_schema(meta_schema), http.OK
