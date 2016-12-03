import logging
import uuid
import urlparse

import requests

from framework.celery_tasks import app as celery_app

from website import settings


logger = logging.getLogger(__name__)


@celery_app.task(ignore_results=True)
def on_preprint_updated(preprint_id):
    # WARNING: Only perform Read-Only operations in an asynchronous task, until Repeatable Read/Serializable
    # transactions are implemented in View and Task application layers.
    from website.models import PreprintService
    preprint = PreprintService.load(preprint_id)

    if settings.SHARE_URL:
        if not preprint.provider.access_token:
            raise ValueError('No access_token for {}. Unable to send {} to SHARE.'.format(preprint.provider, preprint))
        resp = requests.post('{}api/v2/normalizeddata/'.format(settings.SHARE_URL), json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    'tasks': [],
                    'raw': None,
                    'data': {'@graph': format_preprint(preprint)}
                }
            }
        }, headers={'Authorization': 'Bearer {}'.format(preprint.provider.access_token), 'Content-Type': 'application/vnd.api+json'}, verify=False)
        logger.debug(resp.content)
        resp.raise_for_status()


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
    person = GraphNode('person', **{
        'suffix': user.suffix,
        'given_name': user.given_name,
        'family_name': user.family_name,
        'additional_name': user.middle_names,
    })

    person.attrs['identifiers'] = [GraphNode('agentidentifier', agent=person, uri='mailto:{}'.format(uri)) for uri in user.emails]

    if user.is_registered:
        person.attrs['identifiers'].append(GraphNode('agentidentifier', agent=person, uri=user.profile_image_url()))
        person.attrs['identifiers'].append(GraphNode('agentidentifier', agent=person, uri=urlparse.urljoin(settings.DOMAIN, user.profile_url)))

    person.attrs['related_agents'] = [GraphNode('isaffiliatedwith', subject=person, related=GraphNode('institution', name=institution.name)) for institution in user.affiliated_institutions]

    return person


def format_contributor(preprint, user, bibliographic, index):
    return GraphNode(
        'creator' if bibliographic else 'contributor',
        agent=format_user(user),
        order_cited=index if bibliographic else None,
        creative_work=preprint,
        cited_as=user.fullname,
    )


def format_preprint(preprint):
    preprint_graph = GraphNode('preprint', **{
        'title': preprint.node.title,
        'description': preprint.node.description or '',
        'is_deleted': not preprint.is_published or not preprint.node.is_public or preprint.node.is_preprint_orphan,
        'date_updated': preprint.date_modified.isoformat(),
        'date_published': preprint.date_published.isoformat() if preprint.date_published else None
    })

    to_visit = [
        preprint_graph,
        GraphNode('workidentifier', creative_work=preprint_graph, uri=urlparse.urljoin(settings.DOMAIN, preprint.url))
    ]

    if preprint.article_doi:
        to_visit.append(GraphNode('workidentifier', creative_work=preprint_graph, uri='http://dx.doi.org/{}'.format(preprint.article_doi)))

    preprint_graph.attrs['tags'] = [
        GraphNode('throughtags', creative_work=preprint_graph, tag=GraphNode('tag', name=tag._id))
        for tag in preprint.node.tags or [] if tag._id
    ]

    preprint_graph.attrs['subjects'] = [
        GraphNode('throughsubjects', creative_work=preprint_graph, subject=GraphNode('subject', name=subject))
        for subject in set(x['text'] for hier in preprint.get_subjects() or [] for x in hier) if subject
    ]

    to_visit.extend(format_contributor(preprint_graph, user, bool(user._id in preprint.node.visible_contributor_ids), i) for i, user in enumerate(preprint.node.contributors))
    to_visit.extend(GraphNode('AgentWorkRelation', creative_work=preprint_graph, agent=GraphNode('institution', name=institution.name)) for institution in preprint.node.affiliated_institutions)

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
