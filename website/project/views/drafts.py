import functools
import httplib as http

from dateutil.parser import parse as parse_date
from flask import request, redirect

from modularodm import Q
from modularodm.exceptions import ValidationValueError

from framework.mongo import database
from framework.mongo.utils import get_or_http_error, autoload
from framework.exceptions import HTTPError
from framework.status import push_status_message

from website.exceptions import NodeStateError
from website.util.permissions import ADMIN
from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
    http_error_if_disk_saving_mode
)
from website import language
from website.project import utils as project_utils
from website.project.model import MetaSchema, DraftRegistration, DraftRegistrationApproval
from website.project.metadata.utils import serialize_meta_schema, serialize_draft_registration
from website.project.utils import serialize_node
from website.util import rapply
from website.util.sanitize import strip_html

get_schema_or_fail = lambda query: get_or_http_error(MetaSchema, query)
autoload_draft = functools.partial(autoload, DraftRegistration, 'draft_id', 'draft')

@autoload_draft
@must_have_permission(ADMIN)
@must_be_valid_project
def submit_draft_for_review(auth, node, draft, *args, **kwargs):
    """Submit for approvals and/or notifications

    :return: serialized registration
    :rtype: dict
    :raises: HTTPError if embargo end date is invalid
    """
    data = request.get_json()
    meta = {}
    registration_choice = data.get('registrationChoice', 'immediate')
    if registration_choice == 'embargo':
        # Initiate embargo
        end_date_string = data['embargoEndDate']
        end_date = parse_date(end_date_string)
        if not node._is_embargo_date_valid(end_date):
            raise HTTPError(http.BAD_REQUEST, data={
                'message_short': 'Invalid embargo end date',
                'message_long': 'Embargo end date must be more than one day in the future.'
            })
        meta['embargo_end_date'] = end_date_string
    meta['registration_choice'] = registration_choice
    approval = DraftRegistrationApproval(
        initiated_by=auth.user,
        meta=meta
    )
    authorizers = draft.get_authorizers()
    for user in authorizers:
        approval.add_authorizer(user)
    approval.save()
    draft.approval = approval
    draft.save()

    push_status_message(language.AFTER_SUBMIT_FOR_REVIEW,
                        kind='info',
                        trust=False)
    return {
        'status': 'initiated',
        'urls': {
            'registrations': node.web_url_for('node_registrations')
        }
    }, http.ACCEPTED

@autoload_draft
@must_have_permission(ADMIN)
@must_be_valid_project
def draft_before_register_page(auth, node, draft, *args, **kwargs):
    """Allow the user to select an embargo period and confirm registration

    :return: serialized Node + DraftRegistration
    :rtype: dict
    """
    ret = serialize_node(node, auth, primary=True)

    ret['draft'] = serialize_draft_registration(draft, auth)
    return ret

@autoload_draft
@must_have_permission(ADMIN)
@must_be_valid_project
@http_error_if_disk_saving_mode
def register_draft_registration(auth, node, draft, *args, **kwargs):
    """Initiate a registration from a draft registration

    :return: success message; url to registrations page
    :rtype: dict
    """
    data = request.get_json()
    register = draft.register(auth)
    draft.save()

    if data.get('registrationChoice', 'immediate') == 'embargo':
        # Initiate embargo
        embargo_end_date = parse_date(data['embargoEndDate'], ignoretz=True)
        try:
            register.embargo_registration(auth.user, embargo_end_date)
        except ValidationValueError as err:
            raise HTTPError(http.BAD_REQUEST, data=dict(message_long=err.message))
    else:
        try:
            register.require_approval(auth.user)
        except NodeStateError as err:
            raise HTTPError(http.BAD_REQUEST, data=dict(message_long=err.message))

    register.save()
    push_status_message(language.AFTER_REGISTER_ARCHIVING,
                        kind='info',
                        trust=False)
    return {
        'status': 'initiated',
        'urls': {
            'registrations': node.web_url_for('node_registrations')
        }
    }, http.ACCEPTED

@autoload_draft
@must_have_permission(ADMIN)
@must_be_valid_project
def get_draft_registration(auth, node, draft, *args, **kwargs):
    """Return a single draft registration

    :return: serialized draft registration
    :rtype: dict
    """
    return serialize_draft_registration(draft, auth), http.OK

@must_have_permission(ADMIN)
@must_be_valid_project
def get_draft_registrations(auth, node, *args, **kwargs):
    """List draft registrations for a node

    :return: serialized draft registrations
    :rtype: dict
    """

    count = request.args.get('count', 100)
    drafts = node.draft_registrations_active[:count]
    return {
        'drafts': [serialize_draft_registration(d, auth) for d in drafts]
    }, http.OK

@must_have_permission(ADMIN)
@must_be_valid_project
def create_draft_registration(auth, node, *args, **kwargs):
    """Create a new draft registration and return it

    :return: serialized draft registration
    :rtype: dict
    """

    data = request.get_json()

    schema_name = data.get('schema_name')
    if not schema_name:
        raise HTTPError(http.BAD_REQUEST)

    schema_version = data.get('schema_version', 1)
    schema_data = data.get('schema_data', {})
    schema_data = rapply(schema_data, strip_html)

    meta_schema = get_schema_or_fail(
        Q('name', 'eq', schema_name) &
        Q('schema_version', 'eq', schema_version)
    )
    draft = node.create_draft_registration(
        user=auth.user,
        schema=meta_schema,
        data=schema_data,
        save=True,
    )
    return serialize_draft_registration(draft, auth), http.CREATED

@must_have_permission(ADMIN)
@must_be_valid_project
def new_draft_registration(auth, node, *args, **kwargs):
    """Create a new draft registration for the node

    :return: Redirect to the new draft's edit page
    :rtype: flask.redirect
    :raises: HTTPError
    """

    data = request.values

    schema_name = data.get('schema_name')
    if not schema_name:
        raise HTTPError(
            http.BAD_REQUEST,
            data={
                'message_short': 'Must specify a schema_name',
                'message_long': 'Please specify a schema_name'
            }
        )

    schema_version = data.get('schema_version', 1)

    # can return 404 if the schema does not exist
    # can return 400 if the schema is in the DB twice (should never happen)
    meta_schema = get_schema_or_fail(
        Q('name', 'eq', schema_name) &
        Q('schema_version', 'eq', int(schema_version))
    )
    draft = node.create_draft_registration(
        user=auth.user,
        schema=meta_schema,
        data={},
        save=True,
    )
    return redirect(node.web_url_for('edit_draft_registration_page', draft_id=draft._id))

@autoload_draft
@must_have_permission(ADMIN)
@must_be_valid_project
def edit_draft_registration_page(auth, node, draft, **kwargs):
    """Draft registration editor

    :return: serialized DraftRegistration
    :rtype: dict
    """
    if draft.registered_node:
        raise HTTPError(http.FORBIDDEN, data={
            'message_short': 'This draft has already been registered.',
            'message_long': 'This draft has already been registered and cannot be modified.'
        })
    ret = project_utils.serialize_node(node, auth, primary=True)
    ret['draft'] = serialize_draft_registration(draft, auth)
    return ret

@autoload_draft
@must_have_permission(ADMIN)
@must_be_valid_project
def update_draft_registration(auth, node, draft, *args, **kwargs):
    """Update an existing draft registration

    :return: serialized draft registration
    :rtype: dict
    :raises: HTTPError
    """
    if draft.registered_node:
        raise HTTPError(http.FORBIDDEN, data={
            'message_short': 'This draft has already been registered.',
            'message_long': 'This draft has already been registered and cannot be modified.'
        })
    data = request.get_json()

    schema_data = data.get('schema_data', {})
    schema_data = rapply(schema_data, strip_html)

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
    draft.save()
    return serialize_draft_registration(draft, auth), http.OK

@autoload_draft
@must_have_permission(ADMIN)
@must_be_valid_project
def delete_draft_registration(auth, node, draft, *args, **kwargs):
    """Permanently delete a draft registration

    :return: None
    :rtype: NoneType
    """
    DraftRegistration.remove_one(draft)
    return None, http.NO_CONTENT

def get_metaschemas(*args, **kwargs):
    """
    List metaschemas with which a draft registration may be created. Only fetch the newest version for each schema.

    :return: serialized metaschemas
    :rtype: dict
    """
    count = request.args.get('count', 100)
    include = request.args.get('include', 'latest')

    meta_schema_collection = database['metaschema']

    meta_schemas = []
    if include == 'latest':
        schema_names = meta_schema_collection.distinct('name')
        for name in schema_names:
            meta_schema_set = MetaSchema.find(Q('name', 'eq', name))
            meta_schemas = meta_schemas + [s for s in meta_schema_set.sort('-schema_version').limit(1)]
    else:
        meta_schemas = MetaSchema.find()

    return {
        'meta_schemas': [
            serialize_meta_schema(ms) for ms in meta_schemas[:count]
        ]
    }, http.OK
