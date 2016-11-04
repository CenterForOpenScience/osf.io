import datetime
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

    if settings.SHARE_URL and settings.SHARE_API_TOKEN:
        resp = requests.post('{}api/v2/normalizeddata/'.format(settings.SHARE_URL), json={
            'created_at': datetime.datetime.utcnow().isoformat(),
            'normalized_data': {
                '@graph': format_preprint(preprint)
            },
        }, headers={'Authorization': 'Bearer {}'.format(settings.SHARE_API_TOKEN)})
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
            if isinstance(value, list):
                ser[key] = [v.ref for v in value]
            elif isinstance(value, GraphNode):
                ser[key] = value.ref
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

    person.attrs['identifiers'] = [
        GraphNode('throughidentifiers', person=person, identifier=GraphNode('identifier', **{
            'url': urlparse.urljoin(settings.DOMAIN, user.profile_url),
            'base_url': settings.DOMAIN
        }))
    ]

    person.attrs['affiliations'] = [GraphNode('affiliation', person=person, entity=GraphNode('institution', name=institution.name)) for institution in user.affiliated_institutions]

    return person


def format_contributor(preprint, user, index):
    person = format_user(user)

    return GraphNode(
        'contributor',
        person=person,
        order_cited=index,
        creative_work=preprint,
        cited_name=user.fullname,
    )


def format_preprint(preprint):
    preprint_graph = GraphNode('preprint', **{
        'title': preprint.node.title,
        'description': preprint.node.description or '',
        'is_deleted': not preprint.is_published or not preprint.node.is_public or preprint.node.is_preprint_orphan,
        'date_updated': preprint.date_modified.isoformat(),
        'date_published': preprint.date_published.isoformat()
    })

    preprint_graph.attrs['links'] = [
        GraphNode('throughlinks', creative_work=preprint_graph, link=GraphNode('link', **{
            'type': 'provider',
            'url': urlparse.urljoin(settings.DOMAIN, preprint.url),
        }))
    ]

    if preprint.article_doi:
        preprint_graph.attrs['links'].append(
            GraphNode('throughlinks', creative_work=preprint_graph, link=GraphNode('link', **{
                'type': 'doi',
                'url': 'http://dx.doi.org/{}'.format(preprint.article_doi.upper().strip('/')),
            }))
        )

    preprint_graph.attrs['subjects'] = [
        GraphNode('throughsubjects', creative_work=preprint_graph, subject=GraphNode('subject', name=tag._id))
        for tag in preprint.node.tags
    ]

    preprint_graph.attrs['subjects'] = [
        GraphNode('throughsubjects', creative_work=preprint_graph, subject=GraphNode('subject', name=subject))
        for subject in set(x['text'] for hier in preprint.get_subjects() for x in hier)
    ]

    preprint_graph.attrs['contributors'] = [format_contributor(preprint_graph, user, i) for i, user in enumerate(preprint.node.contributors)]
    preprint_graph.attrs['institutions'] = [GraphNode('association', creative_work=preprint_graph, entity=GraphNode('institution', name=institution.name)) for institution in preprint.node.affiliated_institutions]

    visited = set()
    to_visit = list(preprint_graph.get_related())

    while True:
        if not to_visit:
            break
        n = to_visit.pop(0)
        if n in visited:
            continue
        visited.add(n)
        to_visit.extend(list(n.get_related()))

    return [node.serialize() for node in visited]
