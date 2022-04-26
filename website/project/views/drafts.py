import functools
from rest_framework import status as http_status
import itertools
import html

from operator import itemgetter

from dateutil.parser import parse as parse_date
from django.utils import timezone
from flask import request, redirect
import pytz

from framework.database import autoload
from framework.exceptions import HTTPError

from osf import features
from osf.utils.sanitize import strip_html
from osf.utils.permissions import ADMIN
from osf.utils.functional import rapply
from osf.models import RegistrationSchema, DraftRegistration

from website.project.decorators import (
    must_be_valid_project,
    must_be_contributor_and_not_group_member,
    must_have_permission,
)
from website import settings
from website.ember_osf_web.decorators import ember_flag_is_active

from website.project import utils
from website.project.metadata.schemas import METASCHEMA_ORDERING
from website.project.metadata.utils import serialize_meta_schema, serialize_draft_registration
from website.project.utils import serialize_node

autoload_draft = functools.partial(autoload, DraftRegistration, 'draft_id', 'draft')

def get_schema_or_fail(schema_name, schema_version):
    try:
        meta_schema = RegistrationSchema.objects.get(name=schema_name, schema_version=schema_version)
    except RegistrationSchema.DoesNotExist:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND, data=dict(
            message_long='No RegistrationSchema record matching that query could be found'
        ))
    return meta_schema

def must_be_branched_from_node(func):
    @autoload_draft
    @must_be_valid_project
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        node = kwargs['node']
        draft = kwargs['draft']
        if draft.deleted:
            raise HTTPError(http_status.HTTP_410_GONE)
        if not draft.branched_from._id == node._id:
            raise HTTPError(
                http_status.HTTP_400_BAD_REQUEST,
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
    end_date = parse_date(end_date_string, ignoretz=True).replace(tzinfo=pytz.utc)
    today = timezone.now()
    if (end_date - today) <= settings.DRAFT_REGISTRATION_APPROVAL_PERIOD:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
            'message_short': 'Invalid embargo end date',
            'message_long': 'Embargo end date for this submission must be at least {0} days in the future.'.format(settings.DRAFT_REGISTRATION_APPROVAL_PERIOD)
        })
    elif not node._is_embargo_date_valid(end_date):
        max_end_date = today + settings.DRAFT_REGISTRATION_APPROVAL_PERIOD
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
            'message_short': 'Invalid embargo end date',
            'message_long': 'Embargo end date must on or before {0}.'.format(max_end_date.isoformat())
        })

def validate_registration_choice(registration_choice):
    if registration_choice not in ('embargo', 'immediate'):
        raise HTTPError(
            http_status.HTTP_400_BAD_REQUEST,
            data={
                'message_short': "Invalid 'registrationChoice'",
                'message_long': "Values for 'registrationChoice' must be either 'embargo' or 'immediate'."
            }
        )

def check_draft_state(draft):
    registered_and_deleted = draft.registered_node and draft.registered_node.is_deleted
    if draft.registered_node and not registered_and_deleted:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN, data={
            'message_short': 'This draft has already been registered',
            'message_long': 'This draft has already been registered and cannot be modified.'
        })


@must_have_permission(ADMIN)
@must_be_contributor_and_not_group_member
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
def get_draft_registration(auth, node, draft, *args, **kwargs):
    """Return a single draft registration

    :return: serialized draft registration
    :rtype: dict
    """
    return serialize_draft_registration(draft, auth), http_status.HTTP_200_OK

@must_have_permission(ADMIN)
@must_be_valid_project
def get_draft_registrations(auth, node, *args, **kwargs):
    """List draft registrations for a node

    :return: serialized draft registrations
    :rtype: dict
    """
    #'updated': '2016-08-03T14:24:12Z'
    count = request.args.get('count', 100)
    drafts = itertools.islice(node.draft_registrations_active, 0, count)
    serialized_drafts = [serialize_draft_registration(d, auth) for d in drafts]
    sorted_serialized_drafts = sorted(serialized_drafts, key=itemgetter('updated'), reverse=True)
    return {
        'drafts': sorted_serialized_drafts
    }, http_status.HTTP_200_OK

@must_have_permission(ADMIN)
@must_be_valid_project
@must_be_contributor_and_not_group_member
@ember_flag_is_active(features.EMBER_CREATE_DRAFT_REGISTRATION)
def new_draft_registration(auth, node, *args, **kwargs):
    """Create a new draft registration for the node

    :return: Redirect to the new draft's edit page
    :rtype: flask.redirect
    :raises: HTTPError
    """
    if node.is_registration:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN, data={
            'message_short': "Can't create draft",
            'message_long': 'Creating draft registrations on registered projects is not allowed.'
        })
    data = request.values

    schema_name = data.get('schema_name')
    if not schema_name:
        raise HTTPError(
            http_status.HTTP_400_BAD_REQUEST,
            data={
                'message_short': 'Must specify a schema_name',
                'message_long': 'Please specify a schema_name'
            }
        )

    schema_version = data.get('schema_version', 2)

    meta_schema = get_schema_or_fail(schema_name, int(schema_version))
    draft = DraftRegistration.create_from_node(
        node=node,
        user=auth.user,
        schema=meta_schema,
        data={}
    )
    return redirect(node.web_url_for('edit_draft_registration_page', draft_id=draft._id, _guid=True))


@must_have_permission(ADMIN)
@must_be_contributor_and_not_group_member
@ember_flag_is_active(features.EMBER_EDIT_DRAFT_REGISTRATION)
@must_be_branched_from_node
def edit_draft_registration_page(auth, node, draft, **kwargs):
    """Draft registration editor

    :return: serialized DraftRegistration
    :rtype: dict
    """
    check_draft_state(draft)
    ret = utils.serialize_node(node, auth, primary=True)
    ret['draft'] = serialize_draft_registration(draft, auth)
    return ret

@must_have_permission(ADMIN)
@must_be_contributor_and_not_group_member
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

    # Unencodes HTML special characters in filenames
    if schema_data.get('uploader', {}).get('value'):
        schema_data['uploader']['value'] = html.unescape(schema_data['uploader']['value'])
    if schema_data.get('uploader', {}).get('extra'):
        for extra in schema_data['uploader']['extra']:
            extra['selectedFileName'] = html.unescape(extra['selectedFileName'])

    schema_name = data.get('schema_name')
    schema_version = data.get('schema_version', 1)
    if schema_name:
        meta_schema = get_schema_or_fail(schema_name, schema_version)
        existing_schema = draft.registration_schema
        if (existing_schema.name, existing_schema.schema_version) != (meta_schema.name, meta_schema.schema_version):
            draft.registration_schema = meta_schema

    draft.update_metadata(schema_data)
    draft.save()
    return serialize_draft_registration(draft, auth), http_status.HTTP_200_OK

@must_have_permission(ADMIN)
@must_be_contributor_and_not_group_member
@must_be_branched_from_node
def delete_draft_registration(auth, node, draft, *args, **kwargs):
    """Permanently delete a draft registration

    :return: None
    :rtype: NoneType
    """
    if draft.registered_node and not draft.registered_node.is_deleted:
        raise HTTPError(
            http_status.HTTP_403_FORBIDDEN,
            data={
                'message_short': 'Can\'t delete draft',
                'message_long': 'This draft has already been registered and cannot be deleted.'
            }
        )
    draft.deleted = timezone.now()
    draft.save(update_fields=['deleted'])
    return None, http_status.HTTP_204_NO_CONTENT


def order_schemas(schema):
    """ Schemas not specified in METASCHEMA_ORDERING get sent to the bottom of the list."""
    try:
        return METASCHEMA_ORDERING.index(schema.name)
    except ValueError:
        return len(METASCHEMA_ORDERING)


def get_metaschemas(*args, **kwargs):
    """
    List metaschemas with which a draft registration may be created. Only fetch the newest version for each schema.

    :return: serialized metaschemas
    :rtype: dict
    """
    count = request.args.get('count', 100)
    include = request.args.get('include', 'latest')

    meta_schemas = RegistrationSchema.objects.filter(active=True)
    if include == 'latest':
        meta_schemas = RegistrationSchema.objects.get_latest_versions()

    meta_schemas = sorted(meta_schemas, key=order_schemas)

    return {
        'meta_schemas': [
            serialize_meta_schema(ms) for ms in meta_schemas[:count]
        ]
    }, http_status.HTTP_200_OK
