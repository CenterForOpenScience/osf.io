import uuid
from django.apps import apps
from urllib.parse import urljoin
import random
import requests
from framework.celery_tasks import app as celery_app
from framework.sentry import log_exception

from website import settings
from celery.exceptions import Retry


class GraphNode(object):

    @property
    def ref(self):
        return {'@id': self.id, '@type': self.type}

    def __init__(self, type_, **attrs):
        self.id = '_:{}'.format(uuid.uuid4())
        self.type = type_.lower()
        self.attrs = attrs

    def get_related(self):
        for value in self.attrs.values():
            if isinstance(value, GraphNode):
                yield value
            elif isinstance(value, list):
                for val in value:
                    yield val

    def serialize(self):
        ser = {}
        for key, value in self.attrs.items():
            if isinstance(value, GraphNode):
                ser[key] = value.ref
            elif isinstance(value, list) or value in {None, ''}:
                continue
            else:
                ser[key] = value

        return dict(self.ref, **ser)


def format_user(user):
    person = GraphNode(
        'person', **{
            'suffix': user.suffix,
            'given_name': user.given_name,
            'family_name': user.family_name,
            'additional_name': user.middle_names,
        }
    )

    person.attrs['identifiers'] = [GraphNode('agentidentifier', agent=person, uri='mailto:{}'.format(uri)) for uri in user.emails.values_list('address', flat=True)]
    person.attrs['identifiers'].append(GraphNode('agentidentifier', agent=person, uri=user.absolute_url))

    if user.external_identity.get('ORCID') and list(user.external_identity['ORCID'].values())[0] == 'VERIFIED':
        person.attrs['identifiers'].append(GraphNode('agentidentifier', agent=person, uri=list(user.external_identity['ORCID'].keys())[0]))

    if user.is_registered:
        person.attrs['identifiers'].append(GraphNode('agentidentifier', agent=person, uri=user.profile_image_url()))

    person.attrs['related_agents'] = [GraphNode('isaffiliatedwith', subject=person, related=GraphNode('institution', name=institution.name)) for institution in user.affiliated_institutions.all()]

    return person


def format_contributor(preprint, user, bibliographic, index):
    return GraphNode(
        'creator' if bibliographic else 'contributor',
        agent=format_user(user),
        order_cited=index if bibliographic else None,
        creative_work=preprint,
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
        is_deleted=False,
        uri=subject.absolute_api_v2_url,
    )
    context[subject.id].attrs['parent'] = format_subject(subject.parent, context)
    context[subject.id].attrs['central_synonym'] = format_subject(subject.bepress_subject, context)
    return context[subject.id]


def send_share_json(resource, data):
    if getattr(resource, 'provider') and resource.provider.access_token:
        access_token = resource.provider.access_token
    else:
        access_token = settings.SHARE_API_TOKEN

    return requests.post(
        f'{settings.SHARE_URL}api/v2/normalizeddata/',
        json=data,
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/vnd.api+json',
        },
    )


def serialize_share_data(resource, old_subjects=None):
    """
    This sends Node/Preprint/Registration data to share.
    :param resource: either a Node, Preprint or Registration
    :param old_subjects:
    :return:
    """
    from osf.models import (
        Node,
        Preprint,
        Registration,
    )

    if isinstance(resource, Preprint):
        serializer = format_preprint
    elif isinstance(resource, Node):
        serializer = format_node
    elif isinstance(resource, Registration):
        serializer = format_registration
    else:
        raise NotImplementedError()

    return {
        'data': {
            'type': 'NormalizedData',
            'attributes': {
                'tasks': [],
                'raw': None,
                'data': {'@graph': serializer(resource, old_subjects)},
            },
        },
    }


def format_preprint(preprint, old_subjects=None):
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
                or preprint.is_spammy
                or is_qa_resource(preprint)
            ),
            'date_updated': preprint.modified.isoformat(),
            'date_published': preprint.date_published.isoformat() if preprint.date_published else None,
        }
    )
    to_visit = [
        preprint_graph,
        GraphNode('workidentifier', creative_work=preprint_graph, uri=urljoin(settings.DOMAIN, preprint._id + '/')),
    ]

    if preprint.get_identifier('doi'):
        to_visit.append(GraphNode('workidentifier', creative_work=preprint_graph, uri='https://doi.org/{}'.format(preprint.get_identifier('doi').value)))

    if preprint.provider.domain_redirect_enabled:
        to_visit.append(GraphNode('workidentifier', creative_work=preprint_graph, uri=preprint.absolute_url))

    if preprint.article_doi:
        # Article DOI refers to a clone of this preprint on another system and therefore does not qualify as an identifier for this preprint
        related_work = GraphNode('creativework')
        to_visit.append(GraphNode('workrelation', subject=preprint_graph, related=related_work))
        to_visit.append(GraphNode('workidentifier', creative_work=related_work, uri='https://doi.org/{}'.format(preprint.article_doi)))

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

    to_visit.extend(format_contributor(preprint_graph, user, preprint.get_visible(user), i) for i, user in enumerate(preprint.contributors))

    visited = set()
    to_visit.extend(preprint_graph.get_related())

    while True:
        if not to_visit:
            break
        n = to_visit.pop(0)
        if n in visited:
            continue
        visited.add(n)
        to_visit.extend(list(n.get_related()))

    return [node.serialize() for node in visited]


def format_node(node, *args, **kwargs):
    is_qa = is_qa_resource(node)

    if node.provider:
        share_publish_type = node.provider.share_publish_type
    else:
        share_publish_type = 'project'

    return [
        {
            '@id': '_:123',
            '@type': 'workidentifier',
            'creative_work': {'@id': '_:789', '@type': 'project'},
            'uri': '{}{}/'.format(settings.DOMAIN, node._id),
        }, {
            '@id': '_:789',
            '@type': share_publish_type,
            'is_deleted': not node.is_public or node.is_deleted or node.is_spammy or is_qa,
        },
    ]


def format_registration(registration, *args, **kwargs):
    is_qa = is_qa_resource(registration)

    registration_graph = GraphNode(
        registration.provider.share_publish_type, **{
            'title': registration.title,
            'description': registration.description or '',
            'is_deleted': not registration.is_public or registration.is_deleted or is_qa,
            'date_published': registration.registered_date.isoformat() if registration.registered_date else None,
            'registration_type': registration.registered_schema.first().name if registration.registered_schema.exists() else None,
            'justification': registration.retraction.justification if registration.retraction else None,
            'withdrawn': registration.is_retracted,
        }
    )

    to_visit = [
        registration_graph,
        GraphNode('workidentifier', creative_work=registration_graph, uri=urljoin(settings.DOMAIN, registration.url)),
    ]

    registration_graph.attrs['tags'] = [
        GraphNode('throughtags', creative_work=registration_graph, tag=GraphNode('tag', name=tag._id))
        for tag in registration.tags.all() or [] if tag._id
    ]

    to_visit.extend(format_contributor(registration_graph, user, bool(user._id in registration.visible_contributor_ids), i) for i, user in enumerate(registration.contributors))
    to_visit.extend(GraphNode('AgentWorkRelation', creative_work=registration_graph, agent=GraphNode('institution', name=institution.name)) for institution in registration.affiliated_institutions.all())

    if registration.parent_node:
        parent = GraphNode('registration')
        to_visit.extend([
            parent,
            GraphNode('workidentifier', creative_work=parent, uri=urljoin(settings.DOMAIN, registration.parent_node.url)),
            GraphNode('ispartof', subject=registration_graph, related=parent),
        ])

    visited = set()
    to_visit.extend(registration_graph.get_related())

    while True:
        if not to_visit:
            break
        n = to_visit.pop(0)
        if n in visited:
            continue
        visited.add(n)
        to_visit.extend(list(n.get_related()))

    return [node_.serialize() for node_ in visited]

def is_qa_resource(resource):
    """
    QA puts tags and special titles on their project to stop them from appearing in the search results. This function
    check if a resource is a 'QA resource' that should be indexed.
    :param resource: should be Node/Registration/Preprint
    :return:
    """
    tags = set(resource.tags.all().values_list('name', flat=True))
    has_qa_tags = bool(set(settings.DO_NOT_INDEX_LIST['tags']).intersection(tags))

    has_qa_title = any(substring in resource.title for substring in settings.DO_NOT_INDEX_LIST['titles'])

    return has_qa_tags or has_qa_title


def update_share(resource, old_subjects=None):
    data = serialize_share_data(resource, old_subjects)
    resp = send_share_json(resource, data)
    status_code = resp.status_code
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        if status_code >= 500:
            async_update_resource_share.delay(resource._id, old_subjects)
        else:
            log_exception()

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
            log_exception()
        elif resp.status_code >= 500:
            try:
                self.retry(
                    exc=e,
                    countdown=(random.random() + 1) * min(60 + settings.CELERY_RETRY_BACKOFF_BASE ** self.request.retries, 60 * 10),
                )
            except Retry:  # Retry is only raise after > 5 retries
                log_exception()
        else:
            log_exception()

    return resp
