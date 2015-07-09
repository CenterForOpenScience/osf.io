from flask import request, redirect
import httplib as http

from modularodm import Q

from framework.mongo.utils import get_or_http_error
from framework.exceptions import HTTPError

from website.util.permissions import ADMIN
from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
)
from framework.auth import Auth
from website.mails import Mail, send_mail
from website.project.utils import serialize_node
from website.project.model import MetaSchema, DraftRegistration, User
from website.project.metadata.utils import serialize_meta_schema, serialize_draft_registration

get_draft_or_fail = lambda pk: get_or_http_error(DraftRegistration, pk)
get_schema_or_fail = lambda query: get_or_http_error(MetaSchema, query)
ADMIN_USERNAMES = ['vndqr', 'szj4b']

@must_be_valid_project
def submit_for_review(node, uid, *args, **kwargs):
    user = User.load(uid)
    auth = Auth(user)

    node.is_pending_review = True

    REVIEW_EMAIL = Mail(tpl_prefix='prereg_review', subject='New Prereg Prize registration ready for review')
    for uid in ADMIN_USERNAMES:
        admin = User.load(uid)
        send_mail(admin.email, REVIEW_EMAIL, user=user, src=node)

    ret = serialize_node(node, auth)
    ret['success'] = True
    return ret

def get_all_draft_registrations(uid, *args, **kwargs):
    user = User.load(uid)
    auth = Auth(user)
    count = request.args.get('count', 100)

    all_drafts = DraftRegistration.find(
        # Q('is_pending_review', 'eq', True) &
        # Q('schema_name', 'eq' 'Prereg Prize')
    )[:count]

    return {
        'drafts': [serialize_draft_registration(d, auth) for d in all_drafts]
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
        registration_metadata=schema_data,
        schema_name = schema_name
    )
    draft.save()
    return serialize_draft_registration(draft, auth), http.CREATED

@must_have_permission(ADMIN)
@must_be_valid_project
def new_draft_registration(auth, node, *args, **kwargs):

    data = request.values

    schema_name = data.get('schema_name')
    if not schema_name:
        raise HTTPError(http.BAD_REQUEST)

    schema_version = data.get('schema_version', 1)
    schema_data = data.get('schema_data', {})

    meta_schema = get_schema_or_fail(
        Q('name', 'eq', schema_name) &
        Q('schema_version', 'eq', int(schema_version))
    )
    draft = DraftRegistration(
        initiator=auth.user,
        branched_from=node,
        registration_schema=meta_schema,
        registration_metadata=schema_data
    )
    draft.save()

    return redirect(node.web_url_for('edit_draft_registration', draft_id=draft._id))

@must_have_permission(ADMIN)
@must_be_valid_project
def edit_draft_registration(auth, node, draft_id, **kwargs):
    draft = DraftRegistration.load(draft_id)
    if not draft:
        raise HTTPError(http.NOT_FOUND)

    ret = serialize_node(node, auth, primary=True)
    ret['draft'] = serialize_draft_registration(draft, auth)
    return ret

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
