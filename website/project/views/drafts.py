import functools
import httplib as http
import datetime
import itertools

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
from website import language, settings
from website.models import NodeLog
from website.prereg import utils as prereg_utils
from website.project import utils as project_utils
from website.project.model import MetaSchema, DraftRegistration
from website.project.metadata.schemas import ACTIVE_META_SCHEMAS
from website.project.metadata.utils import serialize_meta_schema, serialize_draft_registration
from website.project.utils import serialize_node
from website.util import rapply
from website.util.sanitize import strip_html

get_schema_or_fail = lambda query: get_or_http_error(MetaSchema, query)
autoload_draft = functools.partial(autoload, DraftRegistration, 'draft_id', 'draft')

def must_be_branched_from_node(func):
    @autoload_draft
    @must_be_valid_project
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        node = kwargs['node']
        draft = kwargs['draft']
        if not draft.branched_from._id == node._id:
            raise HTTPError(
                http.BAD_REQUEST,
                data={
                    'message_short': 'Not a draft of this node',
                    'message_long': 'This draft registration is not created from the given node.'
                }
            )
        return func(*args, **kwargs)
    return wrapper

def validate_embargo_end_date(end_date_string, node):
    """
    Our reviewers have a window of time in which to review a draft reg. submission.
    If an embargo end_date that is within that window is at risk of causing
    validation errors down the line if the draft is approved and registered.

    The draft registration approval window is always greater than the time span
    for disallowed embargo end dates.

    :raises: HTTPError if end_date is less than the approval window or greater than the
    max embargo end date
    """
    end_date = parse_date(end_date_string, ignoretz=True)
    today = datetime.datetime.utcnow()
    if (end_date - today) <= settings.DRAFT_REGISTRATION_APPROVAL_PERIOD:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid embargo end date',
            'message_long': 'Embargo end date for this submission must be at least {0} days in the future.'.format(settings.DRAFT_REGISTRATION_APPROVAL_PERIOD)
        })
    elif not node._is_embargo_date_valid(end_date):
        max_end_date = today + settings.DRAFT_REGISTRATION_APPROVAL_PERIOD
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid embargo end date',
            'message_long': 'Embargo end date must on or before {0}.'.format(max_end_date.isoformat())
        })

def validate_registration_choice(registration_choice):
    if registration_choice not in ('embargo', 'immediate'):
        raise HTTPError(
            http.BAD_REQUEST,
            data={
                'message_short': "Invalid 'registrationChoice'",
                'message_long': "Values for 'registrationChoice' must be either 'embargo' or 'immediate'."
            }
        )

def check_draft_state(draft):
    registered_and_deleted = draft.registered_node and draft.registered_node.is_deleted
    if draft.registered_node and not registered_and_deleted:
        raise HTTPError(http.FORBIDDEN, data={
            'message_short': 'This draft has already been registered',
            'message_long': 'This draft has already been registered and cannot be modified.'
        })
    if draft.is_pending_review:
        raise HTTPError(http.FORBIDDEN, data={
            'message_short': 'This draft is pending review',
            'message_long': 'This draft is pending review and cannot be modified.'
        })
    if draft.requires_approval and draft.is_approved and (not registered_and_deleted):
        raise HTTPError(http.FORBIDDEN, data={
            'message_short': 'This draft has already been approved',
            'message_long': 'This draft has already been approved and cannot be modified.'
        })

@must_have_permission(ADMIN)
@must_be_branched_from_node
def submit_draft_for_review(auth, node, draft, *args, **kwargs):
    """Submit for approvals and/or notifications

    :return: serialized registration
    :rtype: dict
    :raises: HTTPError if embargo end date is invalid
    """
    data = request.get_json()
    meta = {}
    registration_choice = data.get('registrationChoice', 'immediate')
    validate_registration_choice(registration_choice)
    if registration_choice == 'embargo':
        # Initiate embargo
        end_date_string = data['embargoEndDate']
        validate_embargo_end_date(end_date_string, node)
        meta['embargo_end_date'] = end_date_string
    meta['registration_choice'] = registration_choice
    draft.submit_for_review(
        initiated_by=auth.user,
        meta=meta,
        save=True
    )

    if prereg_utils.get_prereg_schema() == draft.registration_schema:

        node.add_log(
            action=NodeLog.PREREG_REGISTRATION_INITIATED,
            params={'node': node._primary_key},
            auth=auth,
            save=False
        )
        node.save()

    push_status_message(language.AFTER_SUBMIT_FOR_REVIEW,
                        kind='info',
                        trust=False)
    return {
        'status': 'initiated',
        'urls': {
            'registrations': node.web_url_for('node_registrations')
        }
    }, http.ACCEPTED

@must_have_permission(ADMIN)
@must_be_branched_from_node
def draft_before_register_page(auth, node, draft, *args, **kwargs):
    """Allow the user to select an embargo period and confirm registration

    :return: serialized Node + DraftRegistration
    :rtype: dict
    """
    ret = serialize_node(node, auth, primary=True)

    ret['draft'] = serialize_draft_registration(draft, auth)
    return ret


@must_have_permission(ADMIN)
@must_be_branched_from_node
@http_error_if_disk_saving_mode
def register_draft_registration(auth, node, draft, *args, **kwargs):
    """Initiate a registration from a draft registration

    :return: success message; url to registrations page
    :rtype: dict
    """
    data = request.get_json()
    registration_choice = data.get('registrationChoice', 'immediate')
    validate_registration_choice(registration_choice)

    register = draft.register(auth)
    draft.save()

    if registration_choice == 'embargo':
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

@must_have_permission(ADMIN)
@must_be_branched_from_node
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
    drafts = itertools.islice(node.draft_registrations_active, 0, count)
    return {
        'drafts': [serialize_draft_registration(d, auth) for d in drafts]
    }, http.OK

@must_have_permission(ADMIN)
@must_be_valid_project
def new_draft_registration(auth, node, *args, **kwargs):
    """Create a new draft registration for the node

    :return: Redirect to the new draft's edit page
    :rtype: flask.redirect
    :raises: HTTPError
    """
    if node.is_registration:
        raise HTTPError(http.FORBIDDEN, data={
            'message_short': "Can't create draft",
            'message_long': 'Creating draft registrations on registered projects is not allowed.'
        })
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

    schema_version = data.get('schema_version', 2)

    meta_schema = get_schema_or_fail(
        Q('name', 'eq', schema_name) &
        Q('schema_version', 'eq', int(schema_version))
    )
    draft = DraftRegistration.create_from_node(
        node,
        user=auth.user,
        schema=meta_schema,
        data={}
    )
    return redirect(node.web_url_for('edit_draft_registration_page', draft_id=draft._id))


@must_have_permission(ADMIN)
@must_be_branched_from_node
def edit_draft_registration_page(auth, node, draft, **kwargs):
    """Draft registration editor

    :return: serialized DraftRegistration
    :rtype: dict
    """
    check_draft_state(draft)
    ret = project_utils.serialize_node(node, auth, primary=True)
    ret['draft'] = serialize_draft_registration(draft, auth)
    return ret

@must_have_permission(ADMIN)
@must_be_branched_from_node
def update_draft_registration(auth, node, draft, *args, **kwargs):
    """Update an existing draft registration

    :return: serialized draft registration
    :rtype: dict
    :raises: HTTPError
    """
    check_draft_state(draft)
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

@must_have_permission(ADMIN)
@must_be_branched_from_node
def delete_draft_registration(auth, node, draft, *args, **kwargs):
    """Permanently delete a draft registration

    :return: None
    :rtype: NoneType
    """
    if draft.registered_node and not draft.registered_node.is_deleted:
        raise HTTPError(
            http.FORBIDDEN,
            data={
                'message_short': 'Can\'t delete draft',
                'message_long': 'This draft has already been registered and cannot be deleted.'
            }
        )
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
            meta_schema_set = MetaSchema.find(
                Q('name', 'eq', name) &
                Q('schema_version', 'eq', 2)
            )
            meta_schemas = meta_schemas + [s for s in meta_schema_set]
    else:
        meta_schemas = MetaSchema.find()
    meta_schemas = [
        schema
        for schema in meta_schemas
        if schema.name in ACTIVE_META_SCHEMAS
    ]
    meta_schemas.sort(key=lambda a: ACTIVE_META_SCHEMAS.index(a.name))
    return {
        'meta_schemas': [
            serialize_meta_schema(ms) for ms in meta_schemas[:count]
        ]
    }, http.OK
