# -*- coding: utf-8 -*-
import json
import httplib as http
from dateutil.parser import parse as parse_date
import itertools

from flask import request
from modularodm import Q
from modularodm.exceptions import NoResultsFound, ValidationValueError

from framework.exceptions import HTTPError
from framework.flask import redirect  # VOL-aware redirect

from framework.status import push_status_message
from framework.mongo.utils import to_mongo
from framework.forms.utils import process_payload, unprocess_payload
from framework.auth.decorators import must_be_signed

from website.archiver import ARCHIVER_SUCCESS, ARCHIVER_FAILURE

from website import settings
from website.exceptions import NodeStateError
from website.project.decorators import (
    must_be_valid_project, must_be_contributor_or_public,
    must_have_permission,
    must_not_be_registration, must_be_registration,
)
from website.identifiers.model import Identifier
from website.identifiers.metadata import datacite_metadata_for_node
from website.project.metadata.schemas import OSF_META_SCHEMAS
from website.project.utils import serialize_node
from website.util.permissions import ADMIN
from website.models import MetaSchema, NodeLog
from website import language
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
    if node.is_pending_retraction:
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
    if node.is_pending_retraction:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Invalid Request',
            'message_long': 'This registration is already pending retraction'
        })
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
        node.retraction.ask(node.active_contributors())
    except NodeStateError as err:
        raise HTTPError(http.FORBIDDEN, data=dict(message_long=err.message))

    return {'redirectUrl': node.web_url_for('view_project')}

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
    register.is_public = False
    for child in register.get_descendants_recursive():
        child.is_public = False
        child.save()
    try:
        if data.get('registrationChoice', 'immediate') == 'embargo':
            # Initiate embargo
            embargo_end_date = parse_date(data['embargoEndDate'], ignoretz=True)
            register.embargo_registration(auth.user, embargo_end_date)
        else:
            register.require_approval(auth.user)
        register.save()
    except ValidationValueError as err:
        raise HTTPError(http.BAD_REQUEST, data=dict(message_long=err.message))

    push_status_message(language.AFTER_REGISTER_ARCHIVING,
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
