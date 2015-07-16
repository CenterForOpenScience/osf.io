from flask import request, redirect
import httplib as http
from dateutil.parser import parse as parse_date

from modularodm import Q
from modularodm.exceptions import ValidationValueError

from framework import status
from framework.mongo.utils import get_or_http_error
from framework.exceptions import HTTPError
from framework.status import push_status_message
from framework.auth.decorators import must_be_logged_in

from website.util.permissions import ADMIN
from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
    http_error_if_disk_saving_mode
)
from website import settings
from website.admin.model import Role
from website.mails import Mail, send_mail
from website.project import utils as project_utils
from website.project.model import MetaSchema, DraftRegistration
from website.project.metadata.utils import serialize_meta_schema, serialize_draft_registration
from website.project.utils import serialize_node

get_draft_or_fail = lambda pk: get_or_http_error(DraftRegistration, pk)
get_schema_or_fail = lambda query: get_or_http_error(MetaSchema, query)

@must_have_permission(ADMIN)
@must_be_valid_project
def submit_draft_for_review(auth, node, draft_pk, *args, **kwargs):
    user = auth.user

    draft = get_draft_or_fail(draft_pk)
    draft.is_pending_review = True
    draft.save()

    REVIEW_EMAIL = Mail(tpl_prefix='prereg_review', subject='New Prereg Prize registration ready for review')
    send_mail(draft.initiator.email, REVIEW_EMAIL, user=user, src=node)

    ret = project_utils.serialize_node(node, auth)
    ret['success'] = True
    return ret

@must_have_permission(ADMIN)
@must_be_valid_project
def draft_before_register_page(auth, node, draft_id, *args, **kwargs):
    ret = serialize_node(node, auth, primary=True)

    draft = get_draft_or_fail(draft_id)
    ret['draft'] = serialize_draft_registration(draft, auth)
    return ret

@must_have_permission(ADMIN)
@must_be_valid_project
def draft_before_register(auth, node, draft_id, *args, **kwargs):
    ret = serialize_node(node, auth, primary=True)

    draft = get_draft_or_fail(draft_id)
    ret['draft'] = serialize_draft_registration(draft, auth)
    return ret

@must_have_permission(ADMIN)
@must_be_valid_project
@http_error_if_disk_saving_mode
def register_draft_registration(auth, node, draft_id, *args, **kwargs):

    data = request.get_json()

    draft = get_draft_or_fail(draft_id)
    register = draft.register(auth)

    if data.get('registrationChoice', 'immediate') == 'embargo':
        embargo_end_date = parse_date(data['embargoEndDate'], ignoretz=True)

        # Initiate embargo
        try:
            register.embargo_registration(auth.user, embargo_end_date)
            register.save()
        except ValidationValueError as err:
            raise HTTPError(http.BAD_REQUEST, data=dict(message_long=err.message))
        if settings.ENABLE_ARCHIVER:
            register.archive_job.meta = {
                'embargo_urls': {
                    contrib._id: project_utils.get_embargo_urls(register, contrib)
                    for contrib in node.active_contributors()
                }
            }
            register.archive_job.save()
    else:
        register.set_privacy('public', auth, log=False)
        for child in register.get_descendants_recursive(lambda n: n.primary):
            child.set_privacy('public', auth, log=False)

    push_status_message('Files are being copied to the newly created registration, and you will receive an email notification containing a link to the registration when the copying is finished.')

    return {
        'status': 'initiated',
        'urls': {
            'registrations': node.web_url_for('node_registrations')
        }
    }, http.CREATED

@must_be_logged_in
def get_all_draft_registrations(auth, *args, **kwargs):

    group = request.args.get('group')
    count = request.args.get('count', 100)

    query = Q('is_pending_review', 'eq', True)
    if group:
        role = Role.for_user(auth.user, group=group)
        if not role or not role.is_super:
            raise HTTPError(http.FORBIDDEN)
        query = query & Q('fullfills', 'in', group)

    all_drafts = DraftRegistration.find(query)[:count]

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
        Q('branched_from', 'eq', node) &
        Q('initiator', 'eq', auth.user) &
        Q('registered_node', 'eq', None)
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

    messages = draft.before_edit(auth)
    for message in messages:
        status.push_status_message(message)

    ret = project_utils.serialize_node(node, auth, primary=True)
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

    draft.update_metadata(schema_data)
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
