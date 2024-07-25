"""Utilities for pushing metadata to SHARE/Trove

SHARE/Trove accepts metadata records as "indexcards" in turtle format: https://www.w3.org/TR/turtle/
"""
from functools import partial
import logging
import random
from urllib.parse import urljoin
import uuid

from celery.exceptions import Retry
from django.apps import apps
import requests

from framework.celery_tasks import app as celery_app
from framework.celery_tasks.handlers import enqueue_task
from framework.encryption import ensure_bytes
from framework.sentry import log_exception
from osf import models as osf_db
from osf.metadata.tools import pls_gather_metadata_file
from website import settings


logger = logging.getLogger(__name__)


def shtrove_ingest_url():
    return f'{settings.SHARE_URL}api/v3/ingest'


def sharev2_push_url():
    return f'{settings.SHARE_URL}api/v2/normalizeddata/'


def is_qa_resource(resource):
    """
    QA puts tags and special titles on their project to stop them from appearing in the search results. This function
    check if a resource is a 'QA resource' that should be indexed.
    :param resource: should be Node/Registration/Preprint
    :return:
    """
    tags = set(resource.tags.all().values_list('name', flat=True))
    has_qa_tags = bool(set(settings.DO_NOT_INDEX_LIST['tags']).intersection(tags))

    has_qa_title = False
    _title = getattr(resource, 'title', None)
    if _title:
        has_qa_title = any((_substring in _title) for _substring in settings.DO_NOT_INDEX_LIST['titles'])

    return has_qa_tags or has_qa_title


def update_share(resource):
    if not settings.SHARE_ENABLED:
        return
    if not hasattr(resource, 'guids'):
        logger.error(f'update_share called on non-guid resource: {resource}')
        return
    _enqueue_update_share(resource)


def _enqueue_update_share(osfresource):
    _osfguid_value = osfresource.guids.values_list('_id', flat=True).first()
    if not _osfguid_value:
        logger.warning(f'update_share skipping resource that has no guids: {osfresource}')
        return
    enqueue_task(task__update_share.s(_osfguid_value))
    if isinstance(osfresource, (osf_db.AbstractNode, osf_db.Preprint)):
        enqueue_task(async_update_resource_share.s(_osfguid_value))


@celery_app.task(bind=True, max_retries=4, acks_late=True)
def task__update_share(self, guid: str, is_backfill=False):
    """
    This function updates share  takes Preprints, Projects and Registrations.
    :param self:
    :param guid:
    :return:
    """
    resp = _do_update_share(guid, is_backfill=is_backfill)
    try:
        resp.raise_for_status()
    except Exception as e:
        if self.request.retries == self.max_retries:
            log_exception(e)
        elif resp.status_code >= 500:
            try:
                self.retry(
                    exc=e,
                    countdown=(random.random() + 1) * min(60 + settings.CELERY_RETRY_BACKOFF_BASE ** self.request.retries, 60 * 10),
                )
            except Retry as e:  # Retry is only raise after > 5 retries
                log_exception(e)
        else:
            log_exception(e)

    return resp


def pls_send_trove_indexcard(osf_item, *, is_backfill=False):
    try:
        _iri = osf_item.get_semantic_iri()
    except (AttributeError, ValueError):
        raise ValueError(f'could not get iri for {osf_item}')
    _metadata_record = pls_gather_metadata_file(osf_item, 'turtle')
    _queryparams = {
        'focus_iri': _iri,
        'record_identifier': _shtrove_record_identifier(osf_item),
    }
    if is_backfill:
        _queryparams['nonurgent'] = True
    return requests.post(
        shtrove_ingest_url(),
        params=_queryparams,
        headers={
            'Content-Type': _metadata_record.mediatype,
            **_shtrove_auth_headers(osf_item),
        },
        data=ensure_bytes(_metadata_record.serialized_metadata),
    )


def pls_delete_trove_indexcard(osf_item):
    return requests.delete(
        shtrove_ingest_url(),
        params={
            'record_identifier': _shtrove_record_identifier(osf_item),
        },
        headers=_shtrove_auth_headers(osf_item),
    )


def _do_update_share(osfguid: str, *, is_backfill=False):
    logger.debug('%s._do_update_share("%s", is_backfill=%s)', __name__, osfguid, is_backfill)
    _guid_instance = apps.get_model('osf.Guid').load(osfguid)
    if _guid_instance is None:
        raise ValueError(f'unknown osfguid "{osfguid}"')
    _resource = _guid_instance.referent
    _response = (
        pls_delete_trove_indexcard(_resource)
        if _should_delete_indexcard(_resource)
        else pls_send_trove_indexcard(_resource, is_backfill=is_backfill)
    )
    return _response


def _shtrove_record_identifier(osf_item):
    return osf_item.guids.values_list('_id', flat=True).first()


def _shtrove_auth_headers(osf_item):
    _nonfile_item = (
        osf_item.target
        if hasattr(osf_item, 'target')
        else osf_item
    )
    _access_token = (
        _nonfile_item.provider.access_token
        if getattr(_nonfile_item, 'provider', None) and _nonfile_item.provider.access_token
        else settings.SHARE_API_TOKEN
    )
    return {'Authorization': f'Bearer {_access_token}'}


def _should_delete_indexcard(osf_item):
    if getattr(osf_item, 'is_deleted', False) or getattr(osf_item, 'deleted', None):
        return True
    # if it quacks like BaseFileNode, look at .target instead
    _containing_item = getattr(osf_item, 'target', None)
    if _containing_item:
        return not osf_item.should_update_search or _should_delete_indexcard(_containing_item)
    return (
        not _is_item_public(osf_item)
        or getattr(osf_item, 'is_spam', False)
        or is_qa_resource(osf_item)
    )


def _is_item_public(guid_referent) -> bool:
    if hasattr(guid_referent, 'verified_publishable'):
        return guid_referent.verified_publishable        # quacks like Preprint
    return getattr(guid_referent, 'is_public', False)    # quacks like AbstractNode


###
# BEGIN soon-to-be-deleted (🤞) legacy sharev2 push
# (until dust has settled on iri-centric (rdf-based) search)
"""Utilities for pushing metadata to SHARE

SHARE uses a specific dialect of JSON-LD that could/should have been
an internal implementation detail, but for historical reasons OSF must
be aware of it in order to push metadata updates to SHARE -- hopefully,
that awareness is contained entirely within this file.

WARNING: In this context, "graph node" does NOT have anything to do with
OSF's `Node` model, but instead refers to a "node object" within a JSON-LD
graph, as defined at https://www.w3.org/TR/json-ld11/#dfn-node-object

Each graph node must contain '@id' and '@type', plus other key/value pairs
according to the "SHARE schema":
https://github.com/CenterForOpenScience/SHARE/blob/develop/share/schema/schema-spec.yaml

In this case, '@id' will always be a "blank" identifier, which begins with '_:'
and is used only to define relationships between nodes in the graph -- nodes
may reference each other with @id/@type pairs --
e.g. {'@id': '...', '@type': '...'}

Example serialization: The following SHARE-style JSON-LD document represents a
preprint with one "creator" and one identifier -- the graph contains nodes for
the preprint, person, and identifier, plus another node representing the
"creator" relationship between the preprint and person:
```
{
    'central_node_id': '_:foo',
    '@graph': [
        {
            '@id': '_:foo',
            '@type': 'preprint',
            'title': 'This is a preprint!',
        },
        {
            '@id': '_:bar',
            '@type': 'workidentifier',
            'uri': 'https://osf.io/foobar/',
            'creative_work': {'@id': '_:foo', '@type': 'preprint'}
        },
        {
            '@id': '_:baz',
            '@type': 'person',
            'name': 'Magpie Jones'
        },
        {
            '@id': '_:qux',
            '@type': 'creator',
            'creative_work': {'@id': '_:foo', '@type': 'preprint'},
            'agent': {'@id': '_:baz', '@type': 'person'}
        }
    ]
}
```
"""


class GraphNode:
    """Utility class for building a JSON-LD graph suitable for pushing to SHARE

    WARNING: In this context, "graph node" does NOT have anything to do with
    OSF's `Node` model, but instead refers to a "node object" within a JSON-LD
    graph, as defined at https://www.w3.org/TR/json-ld11/#dfn-node-object
    """

    @staticmethod
    def serialize_graph(central_graph_node, all_graph_nodes):
        """Serialize the mess of GraphNodes to a JSON-friendly dictionary
        :param central_graph_node: the GraphNode for the preprint/node/registration
                                   this graph is most "about"
        :param all_graph_nodes: list of GraphNodes to include -- will also recursively
                                look for and include GraphNodes contained in attrs
        """
        to_visit = [central_graph_node, *all_graph_nodes]  # make a copy of the list
        visited = set()
        while to_visit:
            n = to_visit.pop(0)
            if n not in visited:
                visited.add(n)
                to_visit.extend(n.get_related())

        return {
            'central_node_id': central_graph_node.id,
            '@graph': [node.serialize() for node in visited],
        }

    @property
    def ref(self):
        return {'@id': self.id, '@type': self.type}

    def __init__(self, type_, **attrs):
        self.id = f'_:{uuid.uuid4()}'
        self.type = type_.lower()
        self.attrs = attrs

    def get_related(self):
        for value in self.attrs.values():
            if isinstance(value, GraphNode):
                yield value
            elif isinstance(value, list):
                yield from value

    def serialize(self):
        ser = {}
        for key, value in self.attrs.items():
            if isinstance(value, GraphNode):
                ser[key] = value.ref
            elif isinstance(value, list) or value in (None, '', {}):
                continue
            else:
                ser[key] = value

        return dict(self.ref, **ser)


def format_user(user):
    person = GraphNode(
        'person', **{
            'name': user.fullname,
            'suffix': user.suffix,
            'given_name': user.given_name,
            'family_name': user.family_name,
            'additional_name': user.middle_names,
        },
    )

    person.attrs['identifiers'] = [GraphNode('agentidentifier', agent=person, uri=user.absolute_url)]

    if user.external_identity.get('ORCID') and list(user.external_identity['ORCID'].values())[0] == 'VERIFIED':
        person.attrs['identifiers'].append(GraphNode('agentidentifier', agent=person, uri=list(user.external_identity['ORCID'].keys())[0]))

    person.attrs['related_agents'] = [GraphNode('isaffiliatedwith', subject=person, related=GraphNode('institution', name=institution.name)) for institution in user.get_affiliated_institutions()]

    return person


def format_bibliographic_contributor(work_node, user, index):
    return GraphNode(
        'creator',
        agent=format_user(user),
        order_cited=index,
        creative_work=work_node,
        cited_as=user.fullname,
    )


def format_subject(subject, context=None):
    if context is None:
        context = {}
    if subject is None:
        return None
    if subject.id in context:
        return context[subject.id]
    context[subject.id] = GraphNode(
        'subject',
        name=subject.text,
        uri=subject.absolute_api_v2_url,
    )
    context[subject.id].attrs['parent'] = format_subject(subject.parent, context)
    context[subject.id].attrs['central_synonym'] = format_subject(subject.bepress_subject, context)
    return context[subject.id]


def send_share_json(resource, data):
    """POST metadata to SHARE, using the provider for the given resource.
    """
    if getattr(resource, 'provider') and resource.provider.access_token:
        access_token = resource.provider.access_token
    else:
        access_token = settings.SHARE_API_TOKEN

    return requests.post(
        sharev2_push_url(),
        json=data,
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/vnd.api+json',
        },
    )


def serialize_share_data(resource, old_subjects=None):
    """Build a request payload to send Node/Preprint/Registration metadata to SHARE.
    :param resource: either a Node, Preprint or Registration
    :param old_subjects:

    :return: JSON-serializable dictionary of the resource's metadata, good for POSTing to SHARE
    """
    from osf.models import (
        Node,
        DraftNode,
        Preprint,
        Registration,
    )

    if isinstance(resource, Preprint):
        # old_subjects is only used for preprints and should be removed as soon as SHARE
        # is fully switched over to the non-mergy pipeline (see ENG-2098)
        serializer = partial(serialize_preprint, old_subjects=old_subjects)
    elif isinstance(resource, Node):
        serializer = serialize_osf_node
    elif isinstance(resource, Registration):
        serializer = serialize_registration
    elif isinstance(resource, DraftNode):
        return {}
    else:
        raise NotImplementedError()

    return {
        'data': {
            'type': 'NormalizedData',
            'attributes': {
                'tasks': [],
                'raw': None,
                'suid': resource._id,
                'data': serializer(resource),
            },
        },
    }


def serialize_preprint(preprint, old_subjects=None):
    if old_subjects is None:
        old_subjects = []
    from osf.models import Subject
    old_subjects = [Subject.objects.get(id=s) for s in old_subjects]
    preprint_graph = GraphNode(
        preprint.provider.share_publish_type, **{
            'title': preprint.title,
            'description': preprint.description or '',
            'is_deleted': (
                (not preprint.verified_publishable and not preprint.is_retracted)
                or preprint.is_spam
                or preprint.is_deleted
                or is_qa_resource(preprint)
            ),
            'date_updated': preprint.modified.isoformat(),
            'date_published': preprint.date_published.isoformat() if preprint.date_published else None,
        },
    )
    to_visit = [
        preprint_graph,
        GraphNode('workidentifier', creative_work=preprint_graph, uri=urljoin(settings.DOMAIN, preprint._id + '/')),
    ]

    doi = preprint.get_identifier_value('doi')
    if doi:
        to_visit.append(GraphNode('workidentifier', creative_work=preprint_graph, uri=f'{settings.DOI_URL_PREFIX}{doi}'))

    if preprint.provider.domain_redirect_enabled:
        to_visit.append(GraphNode('workidentifier', creative_work=preprint_graph, uri=preprint.absolute_url))

    if preprint.article_doi:
        # Article DOI refers to a clone of this preprint on another system and therefore does not qualify as an identifier for this preprint
        related_work = GraphNode('creativework')
        to_visit.append(GraphNode('workrelation', subject=preprint_graph, related=related_work))
        to_visit.append(GraphNode('workidentifier', creative_work=related_work, uri=f'{settings.DOI_URL_PREFIX}{preprint.article_doi}'))

    preprint_graph.attrs['tags'] = [
        GraphNode('throughtags', creative_work=preprint_graph, tag=GraphNode('tag', name=tag))
        for tag in preprint.tags.values_list('name', flat=True) if tag
    ]

    current_subjects = [
        GraphNode('throughsubjects', creative_work=preprint_graph, is_deleted=False, subject=format_subject(s))
        for s in preprint.subjects.all()
    ]
    deleted_subjects = [
        GraphNode('throughsubjects', creative_work=preprint_graph, is_deleted=True, subject=format_subject(s))
        for s in old_subjects if not preprint.subjects.filter(id=s.id).exists()
    ]
    preprint_graph.attrs['subjects'] = current_subjects + deleted_subjects

    to_visit.extend(format_bibliographic_contributor(preprint_graph, user, i) for i, user in enumerate(preprint.visible_contributors))

    return GraphNode.serialize_graph(preprint_graph, to_visit)

def format_node_lineage(child_osf_node, child_graph_node):
    parent_osf_node = child_osf_node.parent_node
    if not parent_osf_node:
        return []
    parent_graph_node = GraphNode('registration', title=parent_osf_node.title)
    return [
        parent_graph_node,
        GraphNode('workidentifier', creative_work=parent_graph_node, uri=urljoin(settings.DOMAIN, parent_osf_node.url)),
        GraphNode('ispartof', subject=child_graph_node, related=parent_graph_node),
        *format_node_lineage(parent_osf_node, parent_graph_node),
    ]

def serialize_registration(registration):
    return serialize_osf_node(
        registration,
        additional_attrs={
            'date_published': registration.registered_date.isoformat() if registration.registered_date else None,
            'registration_type': registration.registered_schema.first().name if registration.registered_schema.exists() else None,
            'justification': registration.retraction.justification if registration.retraction else None,
            'withdrawn': registration.is_retracted,
            'extra': {'osf_related_resource_types': _get_osf_related_resource_types(registration)},
        },
    )

def _get_osf_related_resource_types(registration):
    from osf.models import OutcomeArtifact
    from osf.utils.outcomes import ArtifactTypes
    artifacts = OutcomeArtifact.objects.for_registration(registration).filter(finalized=True, deleted__isnull=True)
    return {
        artifact_type.name.lower(): artifacts.filter(artifact_type=artifact_type).exists()
        for artifact_type in ArtifactTypes.public_types()
    }

def serialize_osf_node(osf_node, additional_attrs=None):
    if osf_node.provider:
        share_publish_type = osf_node.provider.share_publish_type
    else:
        share_publish_type = 'project'

    graph_node = GraphNode(
        share_publish_type, **{
            'title': osf_node.title,
            'description': osf_node.description or '',
            'is_deleted': (
                not osf_node.is_public
                or osf_node.is_deleted
                or osf_node.is_spam
                or is_qa_resource(osf_node)
            ),
            **(additional_attrs or {}),
        },
    )

    to_visit = [
        graph_node,
        GraphNode('workidentifier', creative_work=graph_node, uri=urljoin(settings.DOMAIN, osf_node.url)),
    ]

    doi = osf_node.get_identifier_value('doi')
    if doi:
        to_visit.append(GraphNode('workidentifier', creative_work=graph_node, uri=f'{settings.DOI_URL_PREFIX}{doi}'))

    graph_node.attrs['tags'] = [
        GraphNode('throughtags', creative_work=graph_node, tag=GraphNode('tag', name=tag._id))
        for tag in osf_node.tags.all()
    ]

    graph_node.attrs['subjects'] = [
        GraphNode('throughsubjects', creative_work=graph_node, subject=format_subject(s))
        for s in osf_node.subjects.all()
    ]

    to_visit.extend(format_bibliographic_contributor(graph_node, user, i) for i, user in enumerate(osf_node.visible_contributors))
    to_visit.extend(GraphNode('AgentWorkRelation', creative_work=graph_node, agent=GraphNode('institution', name=institution.name)) for institution in osf_node.affiliated_institutions.all())

    to_visit.extend(format_node_lineage(osf_node, graph_node))

    return GraphNode.serialize_graph(graph_node, to_visit)


@celery_app.task(bind=True, max_retries=4, acks_late=True)
def async_update_resource_share(self, guid, old_subjects=None):
    """
    This function updates share  takes Preprints, Projects and Registrations.
    :param self:
    :param guid:
    :return:
    """
    AbstractNode = apps.get_model('osf.AbstractNode')
    resource = AbstractNode.load(guid)
    if not resource:
        Preprint = apps.get_model('osf.Preprint')
        resource = Preprint.load(guid)

    data = serialize_share_data(resource, old_subjects)
    resp = send_share_json(resource, data)
    try:
        resp.raise_for_status()
    except Exception as e:
        if self.request.retries == self.max_retries:
            log_exception(e)
        elif resp.status_code >= 500:
            try:
                self.retry(
                    exc=e,
                    countdown=(random.random() + 1) * min(60 + settings.CELERY_RETRY_BACKOFF_BASE ** self.request.retries, 60 * 10),
                )
            except Retry as e:  # Retry is only raise after > 5 retries
                log_exception(e)
        else:
            log_exception(e)

    return resp
