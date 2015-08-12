# -*- coding: utf-8 -*-
import json
import httplib as http
from dateutil.parser import parse as parse_date
import itertools

from flask import request
from modularodm import Q
from modularodm.exceptions import NoResultsFound, ValidationValueError

from framework import status
from framework.exceptions import HTTPError, PermissionsError
from framework.flask import redirect  # VOL-aware redirect

from framework.status import push_status_message
from framework.mongo.utils import to_mongo
from framework.forms.utils import process_payload, unprocess_payload
from framework.auth.decorators import must_be_signed

from website.archiver import ARCHIVER_SUCCESS, ARCHIVER_FAILURE

from website import settings
from website.exceptions import (
    InvalidRetractionApprovalToken, InvalidRetractionDisapprovalToken,
    InvalidEmbargoApprovalToken, InvalidEmbargoDisapprovalToken,
    NodeStateError
)
from website.project.decorators import (
    must_be_valid_project, must_be_contributor_or_public,
    must_have_permission,
    must_not_be_registration, must_be_registration,
    must_be_public_registration
)
from website.identifiers.model import Identifier
from website.identifiers.metadata import datacite_metadata_for_node
from website.project.metadata.schemas import OSF_META_SCHEMAS
from website.project.utils import serialize_node
from website.project import utils as project_utils
from website.util.permissions import ADMIN
from website.models import MetaSchema, NodeLog
from website import language, mails
from website.project import signals as project_signals
from website import util

from website.archiver.decorators import fail_archive_on_error

from website.identifiers.client import EzidClient

from .node import _view_project
from .. import clean_template_name


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def node_register_page(auth, node, **kwargs):

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
@must_have_permission(ADMIN)
def node_registration_retraction_get(auth, node, **kwargs):
    """Prepares node object for registration retraction page.

    :return: serialized Node to be retracted
    :raises: 400: BAD_REQUEST if registration already pending retraction
    """

    if not node.is_registration:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid Request',
            'message_long': 'Retractions of non-registrations is not permitted.'
        })
    if node.pending_retraction:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid Request',
            'message_long': 'This registration is already pending a retraction.'
        })

    return serialize_node(node, auth, primary=True)

@must_be_valid_project
@must_have_permission(ADMIN)
def node_registration_retraction_post(auth, node, **kwargs):
    """Handles retraction of public registrations

    :param auth: Authentication object for User
    :return: Redirect URL for successful POST
    """

    if not node.is_registration:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid Request',
            'message_long': 'Retractions of non-registrations is not permitted.'
        })

    if node.root is not node:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid Request',
            'message_long': 'Retraction of non-parent registrations is not permitted.'
        })

    data = request.get_json()
    try:
        node.retract_registration(auth.user, data.get('justification', None))
        node.save()
    except NodeStateError as err:
        raise HTTPError(http.FORBIDDEN, data=dict(message_long=err.message))

    for contributor in node.active_contributors():
        _send_retraction_email(node, contributor)

    return {'redirectUrl': node.web_url_for('view_project')}

def _send_retraction_email(node, user):
    """ Sends Approve/Disapprove email for retraction of a public registration to user
        :param node: Node being retracted
        :param user: Admin user to be emailed
    """

    registration_link = node.web_url_for('view_project', _absolute=True)
    approval_time_span = settings.RETRACTION_PENDING_TIME.days * 24
    initiators_fullname = node.retraction.initiated_by.fullname

    if node.has_permission(user, 'admin'):
        approval_token = node.retraction.approval_state[user._id]['approval_token']
        disapproval_token = node.retraction.approval_state[user._id]['disapproval_token']
        approval_link = node.web_url_for(
            'node_registration_retraction_approve',
            token=approval_token,
            _absolute=True)
        disapproval_link = node.web_url_for(
            'node_registration_retraction_disapprove',
            token=disapproval_token,
            _absolute=True)

        mails.send_mail(
            user.username,
            mails.PENDING_RETRACTION_ADMIN,
            'plain',
            user=user,
            initiated_by=initiators_fullname,
            approval_link=approval_link,
            disapproval_link=disapproval_link,
            registration_link=registration_link,
            approval_time_span=approval_time_span,
        )
    else:
        mails.send_mail(
            user.username,
            mails.PENDING_RETRACTION_NON_ADMIN,
            user=user,
            initiated_by=initiators_fullname,
            registration_link=registration_link
        )

@must_be_valid_project
@must_have_permission(ADMIN)
def node_registration_retraction_approve(auth, node, token, **kwargs):
    """Handles disapproval of registration retractions
    :param auth: User wanting to disapprove retraction
    :return: Redirect to registration or
    :raises: HTTPError if invalid token or user is not admin
    """

    if not node.pending_retraction:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid Token',
            'message_long': 'This registration is not pending a retraction.'
        })

    try:
        node.retraction.approve_retraction(auth.user, token)
        node.retraction.save()
        if node.is_retracted:
            node.update_search()
    except InvalidRetractionApprovalToken as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': e.message_short,
            'message_long': e.message_long
        })
    except PermissionsError as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Unauthorized access',
            'message_long': e.message
        })

    status.push_status_message('Your approval has been accepted.', kind='success', trust=False)
    return redirect(node.web_url_for('view_project'))

@must_be_valid_project
@must_have_permission(ADMIN)
@must_be_public_registration
def node_registration_retraction_disapprove(auth, node, token, **kwargs):
    """Handles approval of registration retractions
    :param auth: User wanting to approve retraction
    :param kwargs:
    :return: Redirect to registration or
    :raises: HTTPError if invalid token or user is not admin
    """

    if not node.pending_retraction:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid Token',
            'message_long': 'This registration is not pending a retraction.'
        })

    try:
        node.retraction.disapprove_retraction(auth.user, token)
        node.retraction.save()
    except InvalidRetractionDisapprovalToken as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': e.message_short,
            'message_long': e.message_long
        })
    except PermissionsError as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Unauthorized access',
            'message_long': e.message
        })

    status.push_status_message('Your disapproval has been accepted and the retraction has been cancelled.', kind='success', trust=False)
    return redirect(node.web_url_for('view_project'))

@must_be_valid_project
@must_have_permission(ADMIN)
def node_registration_embargo_approve(auth, node, token, **kwargs):
    """Handles approval of registration embargoes
    :param auth: User wanting to approve the embargo
    :param kwargs:
    :return: Redirect to registration or
    :raises: HTTPError if invalid token or user is not admin
    """

    if not node.pending_embargo:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid Token',
            'message_long': 'This registration is not pending an embargo.'
        })

    try:
        node.embargo.approve_embargo(auth.user, token)
        node.embargo.save()
    except InvalidEmbargoApprovalToken as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': e.message_short,
            'message_long': e.message_long
        })
    except PermissionsError as e:
        raise HTTPError(http.FORBIDDEN, data={
            'message_short': 'Unauthorized access',
            'message_long': e.message
        })

    status.push_status_message('Your approval has been accepted.', kind='success', trust=False)
    return redirect(node.web_url_for('view_project'))

@must_be_valid_project
@must_have_permission(ADMIN)
def node_registration_embargo_disapprove(auth, node, token, **kwargs):
    """Handles disapproval of registration embargoes
    :param auth: User wanting to disapprove the embargo
    :return: Redirect to registration or
    :raises: HTTPError if invalid token or user is not admin
    """

    if not node.pending_embargo:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid Token',
            'message_long': 'This registration is not pending an embargo.'
        })
    # Note(hryabcki): node.registered_from not accessible after disapproval
    if node.embargo.for_existing_registration:
        redirect_url = node.web_url_for('view_project')
    else:
        redirect_url = node.registered_from.web_url_for('view_project')
    try:
        node.embargo.disapprove_embargo(auth.user, token)
        node.embargo.save()
    except InvalidEmbargoDisapprovalToken as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': e.message_short,
            'message_long': e.message_long
        })
    except PermissionsError as e:
        raise HTTPError(http.FORBIDDEN, data={
            'message_short': 'Unauthorized access',
            'message_long': e.message
        })

    status.push_status_message('Your disapproval has been accepted and the embargo has been cancelled.', kind='success', trust=False)
    return redirect(redirect_url)

@must_be_valid_project
@must_be_contributor_or_public
def node_register_template_page(auth, node, **kwargs):

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
def project_before_register(auth, node, **kwargs):
    """Returns prompt informing user that addons, if any, won't be registered."""

    messages = {
        'full': {
            'addons': set(),
            'message': 'The content and version history of <strong>{0}</strong> will be copied to the registration.',
        },
        'partial': {
            'addons': set(),
            'message': 'The current version of the content in <strong>{0}</strong> will be copied to the registration, but version history will be lost.'
        },
        'none': {
            'addons': set(),
            'message': 'The contents of <strong>{0}</strong> cannot be registered at this time,  and will not be included as part of this registration.',
        },
    }
    errors = {}

    addon_set = [n.get_addons() for n in itertools.chain([node], node.get_descendants_recursive(lambda n: n.primary))]
    for addon in itertools.chain(*addon_set):
        if not addon.complete:
            continue
        archive_errors = getattr(addon, 'archive_errors', None)
        error = None
        if archive_errors:
            error = archive_errors()
            if error:
                errors[addon.config.short_name] = error
                continue
        name = addon.config.short_name
        if name in settings.ADDONS_ARCHIVABLE:
            messages[settings.ADDONS_ARCHIVABLE[name]]['addons'].add(addon.config.full_name)
        else:
            messages['none']['addons'].add(addon.config.full_name)
    error_messages = errors.values()

    prompts = [
        m['message'].format(util.conjunct(m['addons']))
        for m in messages.values() if m['addons']
    ]

    if node.has_pointers_recursive:
        prompts.append(
            language.BEFORE_REGISTER_HAS_POINTERS.format(
                category=node.project_or_component
            )
        )

    return {
        'prompts': prompts,
        'errors': error_messages
    }


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def node_register_template_page_post(auth, node, **kwargs):
    data = request.json

    if settings.DISK_SAVING_MODE:
        raise HTTPError(
            http.METHOD_NOT_ALLOWED,
            redirect_url=node.url
        )

    # Sanitize payload data
    clean_data = process_payload(data)

    template = kwargs['template']
    # TODO: Using json.dumps because node_to_use.registered_meta's values are
    # expected to be strings (not dicts). Eventually migrate all these to be
    # dicts, as this is unnecessary
    schema = MetaSchema.find(
        Q('name', 'eq', template)
    ).sort('-schema_version')[0]

    # Create the registration
    register = node.register_node(
        schema, auth, template, json.dumps(clean_data),
    )

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

    push_status_message('Files are being copied to the newly created registration, and you will receive an email '
                        'notification containing a link to the registration when the copying is finished.',
                        kind='info',
                        trust=False)

    return {
        'status': 'initiated',
        'urls': {
            'registrations': node.web_url_for('node_registrations')
        }
    }, http.CREATED


def _build_ezid_metadata(node):
    """Build metadata for submission to EZID using the DataCite profile. See
    http://ezid.cdlib.org/doc/apidoc.html for details.
    """
    doi = settings.EZID_FORMAT.format(namespace=settings.DOI_NAMESPACE, guid=node._id)
    metadata = {
        '_target': node.absolute_url,
        'datacite': datacite_metadata_for_node(node=node, doi=doi)
    }
    return doi, metadata


def _get_or_create_identifiers(node):
    """
    Note: ARKs include a leading slash. This is stripped here to avoid multiple
    consecutive slashes in internal URLs (e.g. /ids/ark/<ark>/). Frontend code
    that build ARK URLs is responsible for adding the leading slash.
    """
    doi, metadata = _build_ezid_metadata(node)
    client = EzidClient(settings.EZID_USERNAME, settings.EZID_PASSWORD)
    try:
        resp = client.create_identifier(doi, metadata)
        return dict(
            [each.strip('/') for each in pair.strip().split(':')]
            for pair in resp['success'].split('|')
        )
    except HTTPError as error:
        if 'identifier already exists' not in error.message.lower():
            raise
        resp = client.get_identifier(doi)
        doi = resp['success']
        suffix = doi.strip(settings.DOI_NAMESPACE)
        return {
            'doi': doi.replace('doi:', ''),
            'ark': '{0}{1}'.format(settings.ARK_NAMESPACE.replace('ark:', ''), suffix),
        }


@must_be_valid_project
@must_be_contributor_or_public
def node_identifiers_get(node, **kwargs):
    """Retrieve identifiers for a node. Node must be a public registration.
    """
    if not node.is_registration or not node.is_public:
        raise HTTPError(http.BAD_REQUEST)
    return {
        'doi': node.get_identifier_value('doi'),
        'ark': node.get_identifier_value('ark'),
    }


@must_be_valid_project
@must_have_permission(ADMIN)
def node_identifiers_post(auth, node, **kwargs):
    """Create identifier pair for a node. Node must be a public registration.
    """
    # TODO: Fail if `node` is retracted
    if not node.is_registration or not node.is_public:  # or node.is_retracted:
        raise HTTPError(http.BAD_REQUEST)
    if node.get_identifier('doi') or node.get_identifier('ark'):
        raise HTTPError(http.BAD_REQUEST)
    try:
        identifiers = _get_or_create_identifiers(node)
    except HTTPError:
        raise HTTPError(http.BAD_REQUEST)
    for category, value in identifiers.iteritems():
        node.set_identifier_value(category, value)
    node.add_log(
        NodeLog.EXTERNAL_IDS_ADDED,
        params={
            'parent_node': node.parent_id,
            'node': node._id,
            'identifiers': identifiers,
        },
        auth=auth,
    )
    return identifiers, http.CREATED


def get_referent_by_identifier(category, value):
    """Look up identifier by `category` and `value` and redirect to its referent
    if found.
    """
    try:
        identifier = Identifier.find_one(
            Q('category', 'eq', category) &
            Q('value', 'eq', value)
        )
    except NoResultsFound:
        raise HTTPError(http.NOT_FOUND)
    if identifier.referent.url:
        return redirect(identifier.referent.url)
    raise HTTPError(http.NOT_FOUND)

@fail_archive_on_error
@must_be_signed
@must_be_registration
def registration_callbacks(node, payload, *args, **kwargs):
    errors = payload.get('errors')
    src_provider = payload['source']['provider']
    if errors:
        node.archive_job.update_target(
            src_provider,
            ARCHIVER_FAILURE,
            errors=errors,
        )
    else:
        # Dataverse requires two seperate targets, one
        # for draft files and one for published files
        if src_provider == 'dataverse':
            src_provider += '-' + (payload['destination']['name'].split(' ')[-1].lstrip('(').rstrip(')').strip())
        node.archive_job.update_target(
            src_provider,
            ARCHIVER_SUCCESS,
        )
    project_signals.archive_callback.send(node)
